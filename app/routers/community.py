from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..core.database import get_db
from ..routers.auth import get_current_user
from ..models.models import (
    User,
    CollectiveOrder,
    CollectiveMembership,
    CollabPost,
    CollabInterest,
    SupportRegistration,
    DeliveryPreference,
)
from ..schemas.schemas import (
    CollectiveOrderResponse,
    CollabPostCreate,
    CollabPostResponse,
    SupportRegisterRequest,
    SupportStatusResponse,
    DeliveryPreferenceRequest,
    DeliveryPreferenceResponse,
)

router = APIRouter(prefix="/api/community", tags=["community"])

VALID_DELIVERY_METHODS = {"pickup", "standard", "express"}

SUPPORT_BENEFITS = [
    {"icon": "money_off", "title": "Zero commission for 3 months", "desc": "Keep 100% of your sales when you join the support program."},
    {"icon": "star", "title": "Artisan spotlight", "desc": "Get featured on the home page and festival collections."},
    {"icon": "school", "title": "Free skill training", "desc": "Photography, pricing and online-selling workshops in your language."},
    {"icon": "local_shipping", "title": "Delivery help", "desc": "Discounted pickup + packaging support for your first 20 orders."},
    {"icon": "campaign", "title": "Marketing kit", "desc": "Ready-made product photos, reels captions and festival banners."},
    {"icon": "savings", "title": "Low-interest loan", "desc": "Apply for raw-material credit with partner self-help groups."},
]

SUPPORT_SCHEMES = [
    {"id": "general", "title": "Seller Support Program", "desc": "Overall onboarding help for new sellers."},
    {"id": "zero_fee", "title": "Zero-Fee Launch", "desc": "0% commission for 90 days."},
    {"id": "spotlight", "title": "Artisan Spotlight", "desc": "Home-page feature + festival push."},
    {"id": "training", "title": "Skill Training", "desc": "2-week course + certificate + stipend."},
]


def _seed_if_empty(db: Session):
    if db.query(CollectiveOrder).count() == 0:
        db.add_all([
            CollectiveOrder(title="Diwali Bulk Order", product_name="Handmade Clay Diyas (set of 12)",
                            price=299, target_qty=100, joined_qty=64, ends_in="2 days"),
            CollectiveOrder(title="Export Collective", product_name="Block-Print Cotton Fabric (per meter)",
                            price=450, target_qty=200, joined_qty=151, ends_in="5 days"),
            CollectiveOrder(title="Wedding Season Pool", product_name="Brass Decorative Plates",
                            price=899, target_qty=50, joined_qty=12, ends_in="9 days"),
        ])
        db.commit()
    if db.query(CollabPost).count() == 0:
        db.add_all([
            CollabPost(title="Need 500 jute bags in 10 days", type="Need help",
                       description="Big festival order, need 2 artisans for stitching and printing.",
                       author="Sunita Devi", location="Jaipur", interested_count=4),
            CollabPost(title="Sharing teak wood stock", type="Share material",
                       description="Extra seasoned teak available at cost price this month.",
                       author="Karan Mistry", location="Saharanpur", interested_count=7),
            CollabPost(title="Joint blue-pottery dinner set", type="Joint product",
                       description="Potter + painter needed for a 24-piece export dinner set.",
                       author="Blue Pottery Co.", location="Khurja", interested_count=2),
        ])
        db.commit()


@router.get("/collectives", response_model=List[CollectiveOrderResponse])
def list_collectives(current_user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    _seed_if_empty(db)
    orders = db.query(CollectiveOrder).filter(CollectiveOrder.is_active == True).all()  # noqa: E712
    joined_ids = {m.collective_id for m in db.query(CollectiveMembership)
                  .filter(CollectiveMembership.user_id == current_user.id).all()}
    return [CollectiveOrderResponse(
        id=o.id, title=o.title, product_name=o.product_name, price=o.price,
        target_qty=o.target_qty, joined_qty=o.joined_qty, ends_in=o.ends_in,
        joined=o.id in joined_ids) for o in orders]


@router.post("/collectives/{collective_id}/toggle", response_model=CollectiveOrderResponse)
def toggle_collective(collective_id: str,
                      current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    order = db.query(CollectiveOrder).filter(CollectiveOrder.id == collective_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Collective order not found")
    existing = db.query(CollectiveMembership).filter(
        CollectiveMembership.collective_id == collective_id,
        CollectiveMembership.user_id == current_user.id).first()
    if existing:
        db.delete(existing)
        order.joined_qty = max(0, (order.joined_qty or 0) - 1)
        joined = False
    else:
        db.add(CollectiveMembership(collective_id=collective_id, user_id=current_user.id))
        order.joined_qty = (order.joined_qty or 0) + 1
        joined = True
    db.commit()
    db.refresh(order)
    return CollectiveOrderResponse(
        id=order.id, title=order.title, product_name=order.product_name, price=order.price,
        target_qty=order.target_qty, joined_qty=order.joined_qty, ends_in=order.ends_in,
        joined=joined)


@router.get("/collabs", response_model=List[CollabPostResponse])
def list_collabs(current_user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    _seed_if_empty(db)
    posts = db.query(CollabPost).order_by(CollabPost.created_at.desc()).all()
    interested_ids = {i.post_id for i in db.query(CollabInterest)
                      .filter(CollabInterest.user_id == current_user.id).all()}
    return [CollabPostResponse(
        id=p.id, title=p.title, type=p.type, description=p.description or "",
        author=p.author or "", location=p.location or "",
        interested_count=p.interested_count or 0, interested=p.id in interested_ids)
        for p in posts]


@router.post("/collabs", response_model=CollabPostResponse)
def create_collab(payload: CollabPostCreate,
                  current_user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    post = CollabPost(title=payload.title.strip(), type=payload.type,
                      description=payload.description or "",
                      author=current_user.name or "You", location=current_user.location or "",
                      user_id=current_user.id, interested_count=0)
    db.add(post)
    db.commit()
    db.refresh(post)
    return CollabPostResponse(id=post.id, title=post.title, type=post.type,
                              description=post.description or "", author=post.author or "",
                              location=post.location or "", interested_count=0, interested=False)


@router.post("/collabs/{post_id}/toggle", response_model=CollabPostResponse)
def toggle_collab(post_id: str,
                  current_user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    post = db.query(CollabPost).filter(CollabPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    existing = db.query(CollabInterest).filter(
        CollabInterest.post_id == post_id,
        CollabInterest.user_id == current_user.id).first()
    if existing:
        db.delete(existing)
        post.interested_count = max(0, (post.interested_count or 0) - 1)
        interested = False
    else:
        db.add(CollabInterest(post_id=post_id, user_id=current_user.id))
        post.interested_count = (post.interested_count or 0) + 1
        interested = True
    db.commit()
    db.refresh(post)
    return CollabPostResponse(id=post.id, title=post.title, type=post.type,
                              description=post.description or "", author=post.author or "",
                              location=post.location or "",
                              interested_count=post.interested_count or 0,
                              interested=interested)


@router.get("/support/benefits")
def support_benefits():
    return {"success": True, "data": {"benefits": SUPPORT_BENEFITS, "schemes": SUPPORT_SCHEMES}}


@router.get("/support/status", response_model=SupportStatusResponse)
def support_status(current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    reg = db.query(SupportRegistration).filter(
        SupportRegistration.user_id == current_user.id).first()
    if not reg:
        return SupportStatusResponse(registered=False)
    return SupportStatusResponse(registered=True, scheme=reg.scheme, status=reg.status)


@router.post("/support/register", response_model=SupportStatusResponse)
def support_register(payload: SupportRegisterRequest,
                     current_user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    reg = db.query(SupportRegistration).filter(
        SupportRegistration.user_id == current_user.id).first()
    if reg:
        reg.scheme = payload.scheme or reg.scheme
        reg.status = "registered"
    else:
        reg = SupportRegistration(user_id=current_user.id,
                                  scheme=payload.scheme or "general", status="registered")
        db.add(reg)
    db.commit()
    return SupportStatusResponse(registered=True, scheme=reg.scheme, status=reg.status)


@router.get("/delivery", response_model=List[DeliveryPreferenceResponse])
def list_deliveries(current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    prefs = db.query(DeliveryPreference).filter(
        DeliveryPreference.user_id == current_user.id).all()
    return [DeliveryPreferenceResponse(order_id=p.order_id, method=p.method,
                                       open_box=bool(p.open_box)) for p in prefs]


@router.get("/delivery/{order_id}", response_model=DeliveryPreferenceResponse)
def get_delivery(order_id: str,
                 current_user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    pref = db.query(DeliveryPreference).filter(
        DeliveryPreference.user_id == current_user.id,
        DeliveryPreference.order_id == order_id).first()
    if not pref:
        return DeliveryPreferenceResponse(order_id=order_id, method="standard", open_box=False)
    return DeliveryPreferenceResponse(order_id=pref.order_id, method=pref.method,
                                      open_box=bool(pref.open_box))


@router.put("/delivery/{order_id}", response_model=DeliveryPreferenceResponse)
def set_delivery(order_id: str, payload: DeliveryPreferenceRequest,
                 current_user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    if payload.method not in VALID_DELIVERY_METHODS:
        raise HTTPException(status_code=400, detail="Invalid delivery method")
    pref = db.query(DeliveryPreference).filter(
        DeliveryPreference.user_id == current_user.id,
        DeliveryPreference.order_id == order_id).first()
    if pref:
        pref.method = payload.method
        pref.open_box = payload.open_box
    else:
        pref = DeliveryPreference(user_id=current_user.id, order_id=order_id,
                                  method=payload.method, open_box=payload.open_box)
        db.add(pref)
    db.commit()
    db.refresh(pref)
    return DeliveryPreferenceResponse(order_id=pref.order_id, method=pref.method,
                                      open_box=bool(pref.open_box))
