from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, JSON, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ..core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    preferred_language = Column(String, default="en")
    role = Column(String, default="artisan")
    shop_name = Column(String, nullable=True)
    location = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    products = relationship("Product", back_populates="user")
    # Seller side: orders placed ON this user's products.
    orders = relationship("Order", back_populates="user",
                          foreign_keys="Order.user_id")
    # Buyer side: orders this user placed across sellers.
    purchases = relationship("Order", back_populates="buyer",
                             foreign_keys="Order.buyer_id")

class Product(Base):
    __tablename__ = "products"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String, nullable=True)
    craft_type = Column(String, nullable=True)
    material = Column(String, nullable=True)
    colors = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    price = Column(Float, nullable=False)
    min_price = Column(Float, nullable=True)
    max_price = Column(Float, nullable=True)
    quantity = Column(Integer, default=0)
    raw_material_cost = Column(Float, nullable=True)
    labor_cost = Column(Float, nullable=True)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="products")
    images = relationship("ProductImage", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")

class ProductImage(Base):
    __tablename__ = "product_images"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    url = Column(String, nullable=False)
    thumbnail_url = Column(String, nullable=True)
    is_original = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("Product", back_populates="images")

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    buyer_name = Column(String, nullable=False)
    buyer_phone = Column(String, nullable=True)
    buyer_email = Column(String, nullable=True)
    total_amount = Column(Float, nullable=False)
    status = Column(String, default="new")
    buyer_id = Column(String, ForeignKey("users.id"), nullable=True)
    shipping_address = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="orders",
                        foreign_keys=[user_id])
    buyer = relationship("User", back_populates="purchases",
                         foreign_keys=[buyer_id])
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    messages = relationship("ConversationMessage", back_populates="conversation")

class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    intent = Column(String, nullable=True)
    extra_data = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("Conversation", back_populates="messages")


# ---------------------------------------------------------------------------
# Community: collective orders, collaboration, seller support, delivery.
# Global catalog rows (no user FK) + per-user join/interest rows.
# ---------------------------------------------------------------------------

class CollectiveOrder(Base):
    __tablename__ = "collective_orders"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    product_name = Column(String, nullable=False)
    price = Column(Float, nullable=False, default=0)
    target_qty = Column(Integer, nullable=False, default=100)
    joined_qty = Column(Integer, nullable=False, default=0)
    ends_in = Column(String, nullable=True, default="7 days")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    memberships = relationship("CollectiveMembership", back_populates="collective",
                               cascade="all, delete-orphan")


class CollectiveMembership(Base):
    __tablename__ = "collective_memberships"

    id = Column(String, primary_key=True, default=generate_uuid)
    collective_id = Column(String, ForeignKey("collective_orders.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    collective = relationship("CollectiveOrder", back_populates="memberships")


class CollabPost(Base):
    __tablename__ = "collab_posts"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    title = Column(String, nullable=False)
    type = Column(String, nullable=False, default="Need help")
    description = Column(Text, nullable=True, default="")
    author = Column(String, nullable=True, default="Artisan")
    location = Column(String, nullable=True, default="")
    interested_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    interests = relationship("CollabInterest", back_populates="post",
                             cascade="all, delete-orphan")


class CollabInterest(Base):
    __tablename__ = "collab_interests"

    id = Column(String, primary_key=True, default=generate_uuid)
    post_id = Column(String, ForeignKey("collab_posts.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("CollabPost", back_populates="interests")


class SupportRegistration(Base):
    __tablename__ = "support_registrations"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    scheme = Column(String, nullable=True, default="general")
    status = Column(String, nullable=False, default="registered")
    created_at = Column(DateTime, default=datetime.utcnow)


class DeliveryPreference(Base):
    __tablename__ = "delivery_preferences"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    order_id = Column(String, nullable=False)
    method = Column(String, nullable=False, default="standard")
    open_box = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
