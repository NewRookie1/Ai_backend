from typing import Optional
import openai
import base64
import json
import re
from ..core.config import settings
from .model_fallback import chat_create, vision_models

def _parse_product_json(raw: str) -> dict:
    """Extract the product JSON from a model reply.

    Reasoning models often wrap the answer in <think> traces, markdown
    fences, or prose. Strip all of that and decode the first {...} block.
    Raises ValueError if no valid JSON object is found.
    """
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text).strip()
    text = re.sub(r"\s*```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object in model reply")
    return json.loads(text[start:end + 1])


class VisionProvider:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url=settings.GROQ_API_BASE,
        )
    
    async def analyze(
        self,
        image_content: bytes,
        filename: str,
        purpose: Optional[str] = None,
    ) -> dict:
        image_base64 = base64.b64encode(image_content).decode('utf-8')
        
        prompt = """Analyze this image and provide detailed product information as a JSON object with exactly these keys:
{
    "product_name": "name of the product",
    "category": "category (Home Decor, Clothing, Jewelry, Art, Kitchen, Accessories, Furniture, Textiles, Other)",
    "material": "material used",
    "craft_type": "type of craft (Weaving, Pottery, Embroidery, etc)",
    "colors": ["list", "of", "colors"],
    "description": "detailed description",
    "tags": ["relevant", "tags"]
}
Output ONLY the JSON object. No markdown fences, no thinking, no analysis, no explanation, no other text."""
        
        try:
            response = chat_create(
                self.client,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                models=vision_models(),
                max_tokens=500,
            )
            
            raw = response.choices[0].message.content or ""
            result = _parse_product_json(raw)
        except Exception as e:
            result = {
                "product_name": "Unknown Product",
                "category": "Other",
                "description": f"Analysis error: {str(e)}",
            }
        
        return result
    
    async def enhance(self, image_content: bytes) -> dict:
        return {
            "enhanced_image_url": "/processed/enhanced.jpg",
            "original_size": len(image_content),
        }
