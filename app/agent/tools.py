from sqlalchemy.orm import Session

class ToolRegistry:
    ALLOWED_TOOLS = [
        "open_scanner",
        "capture_image",
        "analyze_image",
        "enhance_product_image",
        "identify_product",
        "generate_product_listing",
        "create_product",
        "update_product",
        "delete_product",
        "get_products",
        "search_products",
        "get_product_details",
        "get_market_analysis",
        "get_market_trends",
        "get_product_performance",
        "suggest_product_price",
        "get_orders",
        "get_new_orders",
        "get_pending_orders",
        "get_order_details",
        "cancel_order",
        "update_order",
        "navigate",
        "navigate_back",
        "show_help",
        "confirm_action",
    ]
    
    async def execute(self, tool: str, parameters: dict, user_id: str, db: Session) -> dict:
        if tool not in self.ALLOWED_TOOLS:
            raise ValueError(f"Tool '{tool}' is not allowed")
        
        handler = getattr(self, f"_handle_{tool}", None)
        if handler is None:
            raise ValueError(f"Handler for tool '{tool}' not implemented")
        
        return await handler(parameters, user_id, db)
    
    async def _handle_navigate(self, parameters: dict, user_id: str, db: Session) -> dict:
        return {"action": "navigate", "target": parameters.get("target", "home")}
    
    async def _handle_navigate_back(self, parameters: dict, user_id: str, db: Session) -> dict:
        return {"action": "navigate_back"}
    
    async def _handle_open_scanner(self, parameters: dict, user_id: str, db: Session) -> dict:
        return {"action": "open_scanner"}
    
    async def _handle_capture_image(self, parameters: dict, user_id: str, db: Session) -> dict:
        return {"action": "capture_image"}
    
    async def _handle_analyze_image(self, parameters: dict, user_id: str, db: Session) -> dict:
        return {"action": "analyze_image", "purpose": parameters.get("purpose", "general")}
    
    async def _handle_create_product(self, parameters: dict, user_id: str, db: Session) -> dict:
        from ..models.models import Product
        product = Product(
            user_id=user_id,
            name=parameters.get("name", "New Product"),
            description=parameters.get("description", ""),
            category=parameters.get("category"),
            material=parameters.get("material"),
            craft_type=parameters.get("craft_type"),
            price=parameters.get("price", 0),
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        return {"action": "product_created", "product_id": str(product.id)}
    
    async def _handle_get_products(self, parameters: dict, user_id: str, db: Session) -> dict:
        from ..models.models import Product
        products = db.query(Product).filter(Product.user_id == user_id).all()
        return {"action": "products_listed", "count": len(products)}
    
    async def _handle_get_new_orders(self, parameters: dict, user_id: str, db: Session) -> dict:
        from ..models.models import Order
        orders = db.query(Order).filter(
            Order.user_id == user_id,
            Order.status == "new"
        ).all()
        return {"action": "orders_found", "count": len(orders)}
    
    async def _handle_suggest_price(self, parameters: dict, user_id: str, db: Session) -> dict:
        return {"action": "price_suggestion_requested"}
    
    async def _handle_get_market_analysis(self, parameters: dict, user_id: str, db: Session) -> dict:
        return {"action": "market_analysis_requested"}
    
    async def _handle_get_market_trends(self, parameters: dict, user_id: str, db: Session) -> dict:
        return {"action": "market_trends_requested"}
    
    async def _handle_get_product_performance(self, parameters: dict, user_id: str, db: Session) -> dict:
        return {"action": "product_performance_requested"}
    
    async def _handle_show_help(self, parameters: dict, user_id: str, db: Session) -> dict:
        return {"action": "help_shown"}
    
    async def _handle_confirm_action(self, parameters: dict, user_id: str, db: Session) -> dict:
        return {"action": "confirmation_required", "message": parameters.get("message", "Confirm action?")}
    
    async def _handle_update_product(self, parameters: dict, user_id: str, db: Session) -> dict:
        return {"action": "product_update_requested", "product_id": parameters.get("product_id")}
    
    async def _handle_delete_product(self, parameters: dict, user_id: str, db: Session) -> dict:
        from ..models.models import Product
        product_id = parameters.get("product_id")
        if product_id:
            product = db.query(Product).filter(
                Product.id == product_id,
                Product.user_id == user_id
            ).first()
            if product:
                db.delete(product)
                db.commit()
                return {"action": "product_deleted", "product_id": product_id}
        return {"action": "product_not_found"}
    
    async def _handle_search_products(self, parameters: dict, user_id: str, db: Session) -> dict:
        from ..models.models import Product
        query = parameters.get("query", "")
        products = db.query(Product).filter(
            Product.user_id == user_id,
            Product.name.ilike(f"%{query}%")
        ).all()
        return {"action": "products_searched", "count": len(products)}
    
    async def _handle_get_product_details(self, parameters: dict, user_id: str, db: Session) -> dict:
        return {"action": "product_details_requested", "product_id": parameters.get("product_id")}
    
    async def _handle_get_orders(self, parameters: dict, user_id: str, db: Session) -> dict:
        from ..models.models import Order
        orders = db.query(Order).filter(Order.user_id == user_id).all()
        return {"action": "orders_listed", "count": len(orders)}
    
    async def _handle_get_pending_orders(self, parameters: dict, user_id: str, db: Session) -> dict:
        from ..models.models import Order
        orders = db.query(Order).filter(
            Order.user_id == user_id,
            Order.status == "pending"
        ).all()
        return {"action": "pending_orders_found", "count": len(orders)}
    
    async def _handle_get_order_details(self, parameters: dict, user_id: str, db: Session) -> dict:
        return {"action": "order_details_requested", "order_id": parameters.get("order_id")}
    
    async def _handle_cancel_order(self, parameters: dict, user_id: str, db: Session) -> dict:
        from ..models.models import Order
        order_id = parameters.get("order_id")
        if order_id:
            order = db.query(Order).filter(
                Order.id == order_id,
                Order.user_id == user_id
            ).first()
            if order:
                order.status = "cancelled"
                db.commit()
                return {"action": "order_cancelled", "order_id": order_id}
        return {"action": "order_not_found"}
    
    async def _handle_update_order(self, parameters: dict, user_id: str, db: Session) -> dict:
        from ..models.models import Order
        order_id = parameters.get("order_id")
        new_status = parameters.get("status")
        if order_id and new_status:
            order = db.query(Order).filter(
                Order.id == order_id,
                Order.user_id == user_id
            ).first()
            if order:
                order.status = new_status
                db.commit()
                return {"action": "order_updated", "order_id": order_id, "status": new_status}
        return {"action": "order_not_found"}
    
    async def _handle_enhance_product_image(self, parameters: dict, user_id: str, db: Session) -> dict:
        return {"action": "image_enhancement_requested"}
    
    async def _handle_identify_product(self, parameters: dict, user_id: str, db: Session) -> dict:
        return {"action": "product_identification_requested"}
    
    async def _handle_generate_product_listing(self, parameters: dict, user_id: str, db: Session) -> dict:
        return {"action": "listing_generation_requested"}
    
    async def _handle_update_product(self, parameters: dict, user_id: str, db: Session) -> dict:
        return {"action": "product_update_requested", "product_id": parameters.get("product_id")}
