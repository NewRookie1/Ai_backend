from typing import Optional
import logging
import openai
import base64
import json
import re
from ..core.config import settings
from .model_fallback import is_model_not_found, vision_models

logger = logging.getLogger("artisan_ai.vision")

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
        
        # Walk the vision models: skip dead IDs AND models whose reply has
        # no usable JSON (refusals, prose). First clean parse wins.
        last_error = "no vision model available"
        for model in vision_models():
            try:
                response = self.client.chat.completions.create(
                    model=model,
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
                raw = response.choices[0].message.content or ""
                return _parse_product_json(raw)
            except ValueError as e:
                last_error = f"{model}: {e}"
                logger.warning("Vision parse failed for %s", model)
                continue
            except Exception as e:
                if not is_model_not_found(e):
                    raise
                last_error = f"{model}: not accessible"
                logger.warning("Vision model not accessible: %s", model)
                continue
        
        return {
            "product_name": "Unknown Product",
            "category": "Other",
            "description": f"Analysis error: {last_error}",
        }
    
    async def enhance(self, image_content: bytes) -> dict:
        return {
            "enhanced_image_url": "/processed/enhanced.jpg",
            "original_size": len(image_content),
        }
