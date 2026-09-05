from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    preferred_language: str = "en"
    shop_name: Optional[str] = None
    location: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    token: str
    user: UserResponse

class ProductBase(BaseModel):
    name: str
    description: str
    category: Optional[str] = None
    craft_type: Optional[str] = None
    material: Optional[str] = None
    colors: List[str] = []
    tags: List[str] = []
    price: float
    quantity: int = 0
    raw_material_cost: Optional[float] = None
    labor_cost: Optional[float] = None

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: str
    user_id: str
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class OrderItemResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    total_price: float
    
    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: str
    user_id: str
    buyer_name: str
    buyer_phone: Optional[str] = None
    total_amount: float
    status: str
    items: List[OrderItemResponse]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class VoiceChatRequest(BaseModel):
    current_screen: Optional[str] = None
    conversation_id: Optional[str] = None
    user_language: Optional[str] = "en"

class AgentActionResponse(BaseModel):
    tool: str
    parameters: dict = {}
    requires_confirmation: bool = False
    confirmation_message: Optional[str] = None

class AgentResponse(BaseModel):
    intent: str
    actions: List[AgentActionResponse]
    entities: dict = {}
    confidence: float
    requires_confirmation: bool = False
    response: str
    detected_language: Optional[str] = None
    original_text: Optional[str] = None
    normalized_text: Optional[str] = None

class PriceSuggestionResponse(BaseModel):
    suggested_price: float
    currency: str = "INR"
    price_range: dict
    reasoning: str
    confidence: float
    is_estimate: bool = False
    generated_at: datetime

class MarketAnalysisResponse(BaseModel):
    category: str
    demand_score: float
    average_price: float
    total_listings: int
    trends: List[dict]
    summary: str
    recommendation: Optional[str] = None
    confidence: float
    analyzed_at: datetime
