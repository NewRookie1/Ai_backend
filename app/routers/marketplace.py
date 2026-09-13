from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from pydantic import BaseModel

from ..core.database import get_db
from ..routers.auth import get_current_user
from ..models.models import User, Product, Order, OrderItem
from ..schemas.schemas import ProductResponse, OrderResponse

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])


def _ensure_columns(db: Session):
    """Lightweight migration for pre-existing sqlite/postgres DBs that were
    created before role/buyer_id columns existed (create_all won't ALTER)."""
    stmts = [
        ("users", "role", "ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'artisan'"),
        ("orders", "buyer_id", "ALTER TABLE orders ADD COLUMN buyer_id VARCHAR"),
    ]
    for table, column, ddl in stmts:
        try:
            cols = [r[1] for r in
                    db.execute(text(f"PRAGMA table_info({table})")).fetchall()]
            if cols and column not in cols:
                db.execute(text(ddl))
                db.commit()
            elif not cols:
                # Not sqlite (e.g. postgres): probe information_schema.
                exists = db.execute(text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name=:t AND column_name=:c"
                ), {"t": table, "c": column}).first()
                if not exists:
                    try:
                        db.execute(text(ddl))
                        db.commit()
                    except Exception:
                        db.rollback()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass


def _order_to_response(db: Session, o: Order) -> dict:
    items = []
    for it in db.query(OrderItem).filter(OrderItem.order_id == o.id).all():
        p = db.query(Product).filter(Product.id == it.product_id).first()
        items.append({
            "id": it.id, "product_id": it.product_id,
            "product_name": p.name if p else "Product",
            "quantity": it.quantity, "unit_price": it.unit_price,
            "total_price": it.total_price,
        })
    return {
        "id": o.id, "user_id": o.user_id, "buyer_name": o.buyer_name,
        "buyer_phone": o.buyer_phone, "buyer_id": o.buyer_id,
        "total_amount": o.total_amount, "status": o.status,
        "items": items, "created_at": o.created_at,
        "updated_at": o.updated_at,
    }


class PlaceOrderItem(BaseModel):
    product_id: str
    quantity: int = 1


class PlaceOrderRequest(BaseModel):
    items: List[PlaceOrderItem]
    shipping_address: Optional[str] = None
    buyer_phone: Optional[str] = None


@router.get("/products", response_model=List[ProductResponse])
def browse_products(
    search: Optional[str] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Buyer marketplace: every seller's active products."""
    _ensure_columns(db)
    query = db.query(Product).filter(Product.status == "active")
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    if category:
        query = query.filter(Product.category == category)
    products = query.order_by(Product.created_at.desc()).limit(200).all()
    return [ProductResponse.model_validate(p) for p in products]


@router.get("/products/{product_id}", response_model=ProductResponse)
def marketplace_product(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(
        Product.id == product_id, Product.status == "active").first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse.model_validate(product)


@router.post("/orders", response_model=List[OrderResponse])
def place_order(
    payload: PlaceOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Buyer checkout: groups items per seller into one order each."""
    _ensure_columns(db)
    if not payload.items:
        raise HTTPException(status_code=400, detail="No items in order")

    by_seller: dict = {}
    for line in payload.items:
        if line.quantity <= 0:
            raise HTTPException(status_code=400, detail="Invalid quantity")
        product = db.query(Product).filter(
            Product.id == line.product_id,
            Product.status == "active").first()
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product not found: {line.product_id}")
        if product.quantity is not None and product.quantity < line.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Only {product.quantity} left: {product.name}")
        by_seller.setdefault(product.user_id, []).append((product, line.quantity))

    created: list = []
    for seller_id, lines in by_seller.items():
        total = sum(p.price * q for p, q in lines)
        order = Order(
            user_id=seller_id,
            buyer_id=current_user.id,
            buyer_name=current_user.name,
            buyer_phone=payload.buyer_phone or current_user.phone,
            total_amount=total,
            status="new",
            shipping_address=payload.shipping_address,
        )
        db.add(order)
        db.flush()
        for product, qty in lines:
            db.add(OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=qty,
                unit_price=product.price,
                total_price=product.price * qty,
            ))
            if product.quantity is not None:
                product.quantity = max(0, product.quantity - qty)
        created.append(order)
    db.commit()
    for o in created:
        db.refresh(o)
    return [_order_to_response(db, o) for o in created]


@router.get("/my-orders", response_model=List[OrderResponse])
def my_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Buyer's own purchases across all sellers."""
    _ensure_columns(db)
    orders = db.query(Order).filter(
        Order.buyer_id == current_user.id
    ).order_by(Order.created_at.desc()).all()
    return [_order_to_response(db, o) for o in orders]
