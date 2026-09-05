from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from ..core.database import get_db
from ..routers.auth import get_current_user
from ..models.models import User, Product, ProductImage
from ..schemas.schemas import ProductCreate, ProductResponse

router = APIRouter(prefix="/api/products", tags=["products"])

@router.get("", response_model=list[ProductResponse])
async def get_products(
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Product).filter(Product.user_id == current_user.id)
    
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    
    products = query.order_by(Product.created_at.desc()).all()
    return [ProductResponse.model_validate(p) for p in products]

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.user_id == current_user.id,
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return ProductResponse.model_validate(product)

@router.post("", response_model=ProductResponse)
async def create_product(
    product_data: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = Product(
        user_id=current_user.id,
        name=product_data.name,
        description=product_data.description,
        category=product_data.category,
        craft_type=product_data.craft_type,
        material=product_data.material,
        colors=product_data.colors,
        tags=product_data.tags,
        price=product_data.price,
        quantity=product_data.quantity,
        raw_material_cost=product_data.raw_material_cost,
        labor_cost=product_data.labor_cost,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    
    return ProductResponse.model_validate(product)

@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_data: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.user_id == current_user.id,
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    for key, value in product_data.model_dump().items():
        setattr(product, key, value)
    
    db.commit()
    db.refresh(product)
    
    return ProductResponse.model_validate(product)

@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.user_id == current_user.id,
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(product)
    db.commit()
    
    return {"success": True}

@router.post("/{product_id}/price-suggestion")
async def suggest_price(
    product_id: str,
    raw_material_cost: Optional[float] = None,
    labor_cost: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.user_id == current_user.id,
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    from ..providers.pricing import PricingProvider
    provider = PricingProvider()
    
    suggestion = await provider.suggest_price(
        category=product.category,
        material=product.material,
        craft_type=product.craft_type,
        raw_material_cost=raw_material_cost or product.raw_material_cost,
        labor_cost=labor_cost or product.labor_cost,
        current_price=product.price,
    )
    
    return {
        "success": True,
        "data": suggestion,
    }
