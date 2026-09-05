from typing import Optional
import openai
from ..core.config import settings

class TranslationProvider:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url=settings.GROQ_API_BASE,
        )
    
    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
    ) -> dict:
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
        
        response = self.client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": f"Translate the following text to {target_lang_name}. Return only the translation, no explanations."},
                {"role": "user", "content": text},
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        
        return {
            "translated_text": response.choices[0].message.content,
            "source_language": source_language,
        }
