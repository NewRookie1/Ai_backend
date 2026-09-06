from typing import Optional
import openai
import json
from datetime import datetime
from ..core.config import settings
from .model_fallback import chat_create, text_models

class PricingProvider:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url=settings.GROQ_API_BASE,
        )
    
    async def suggest_price(
        self,
        category: Optional[str] = None,
        material: Optional[str] = None,
        craft_type: Optional[str] = None,
        raw_material_cost: Optional[float] = None,
        labor_cost: Optional[float] = None,
        current_price: Optional[float] = None,
    ) -> dict:
        prompt = f"""As an expert in Indian handicraft pricing, suggest a price for this product:
        
Category: {category or 'Unknown'}
Material: {material or 'Unknown'}
Craft Type: {craft_type or 'Unknown'}
Raw Material Cost: ₹{raw_material_cost or 'Unknown'}
Labor Cost: ₹{labor_cost or 'Unknown'}
Current Price: ₹{current_price or 'Unknown'}

Consider:
1. Market demand for similar products
2. Material and labor costs
3. Artisan value and craftsmanship
4. Competitive pricing
5. Profit margin sustainability

Return JSON format:
{{
    "suggested_price": <number>,
    "currency": "INR",
    "price_range": {{"min": <number>, "max": <number>}},
    "reasoning": "<detailed explanation>",
    "confidence": <0-1>,
    "is_estimate": <boolean>
}}"""
        
        try:
            response = chat_create(
                self.client,
                messages=[
                    {"role": "system", "content": "You are an expert in Indian handicraft pricing. Return only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                models=text_models(),
                temperature=0.7,
                max_tokens=1024,
            )
            
            result = json.loads(response.choices[0].message.content)
            result["generated_at"] = datetime.utcnow().isoformat()
            
            return result
        except Exception as e:
            base_cost = (raw_material_cost or 0) + (labor_cost or 0)
            suggested = base_cost * 2.5 if base_cost > 0 else 500
            
            return {
                "suggested_price": suggested,
                "currency": "INR",
                "price_range": {
                    "min": suggested * 0.8,
                    "max": suggested * 1.3,
                },
                "reasoning": f"Based on estimated costs. Material: ₹{raw_material_cost or 0}, Labor: ₹{labor_cost or 0}. Applied 2.5x multiplier for sustainable profit.",
                "confidence": 0.5,
                "is_estimate": True,
                "generated_at": datetime.utcnow().isoformat(),
            }
