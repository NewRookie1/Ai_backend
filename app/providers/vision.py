from typing import Optional
import openai
import base64
import json
from ..core.config import settings

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
        
        prompt = """Analyze this image and provide detailed product information in JSON format:
{
    "product_name": "name of the product",
    "category": "category (Home Decor, Clothing, Jewelry, Art, Kitchen, Accessories, Furniture, Textiles, Other)",
    "material": "material used",
    "craft_type": "type of craft (Weaving, Pottery, Embroidery, etc)",
    "colors": ["list", "of", "colors"],
    "description": "detailed description",
    "tags": ["relevant", "tags"]
}
Return ONLY the JSON, no other text."""
        
        try:
            response = self.client.chat.completions.create(
                model=settings.GROQ_VISION_MODEL,
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
                max_tokens=500,
            )
            
            result = json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            result = {
                "product_name": "Unknown Product",
                "category": "Other",
                "description": response.choices[0].message.content if response else "Analysis failed",
            }
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
