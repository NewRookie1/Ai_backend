from abc import ABC, abstractmethod
from typing import Optional

class BaseProvider(ABC):
    @abstractmethod
    async def initialize(self):
        pass

class SpeechToTextProvider(BaseProvider):
    async def initialize(self):
        pass
    
    async def transcribe(self, audio_content: bytes, filename: str) -> dict:
        import openai
        from ..core.config import settings
        
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        audio_file = ("audio.wav", audio_content, "audio/wav")
        
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )
        
        return {
            "transcript": response.text,
            "language": getattr(response, 'language', 'en'),
            "confidence": 0.95,
        }

class TranslationProvider(BaseProvider):
    async def initialize(self):
        pass
    
    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
    ) -> dict:
        import openai
        from ..core.config import settings
        
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        lang_map = {
            'en': 'English',
            'mr': 'Marathi',
            'hi': 'Hindi',
            'gu': 'Gujarati',
            'bn': 'Bengali',
            'ta': 'Tamil',
            'te': 'Telugu',
            'kn': 'Kannada',
            'ml': 'Malayalam',
            'pa': 'Punjabi',
        }
        
        target_lang_name = lang_map.get(target_language, target_language)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"Translate the following text to {target_lang_name}. Return only the translation."},
                {"role": "user", "content": text},
            ],
        )
        
        return {
            "translated_text": response.choices[0].message.content,
            "source_language": source_language,
        }

class VisionProvider(BaseProvider):
    async def initialize(self):
        pass
    
    async def analyze(
        self,
        image_content: bytes,
        filename: str,
        purpose: Optional[str] = None,
    ) -> dict:
        import openai
        import base64
        from ..core.config import settings
        
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
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
        
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
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
        
        import json
        try:
            result = json.loads(response.choices[0].message.content)
        except:
            result = {
                "product_name": "Unknown Product",
                "category": "Other",
                "description": response.choices[0].message.content,
            }
        
        return result
    
    async def enhance(self, image_content: bytes) -> dict:
        return {
            "enhanced_image_url": "/processed/enhanced.jpg",
            "original_size": len(image_content),
        }

class LLMProvider(BaseProvider):
    async def initialize(self):
        pass
    
    async def chat(
        self,
        messages: list,
        system_prompt: Optional[str] = None,
    ) -> str:
        import openai
        from ..core.config import settings
        
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=all_messages,
        )
        
        return response.choices[0].message.content

class TextToSpeechProvider(BaseProvider):
    async def initialize(self):
        pass
    
    async def synthesize(self, text: str, language: str = "en") -> bytes:
        import openai
        from ..core.config import settings
        
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text,
        )
        
        return response.content
