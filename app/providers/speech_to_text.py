from typing import Optional
import openai
from ..core.config import settings

class SpeechToTextProvider:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url=settings.GROQ_API_BASE,
        )
    
    async def transcribe(self, audio_content: bytes, filename: str) -> dict:
        try:
            audio_file = ("audio.wav", audio_content, "audio/wav")
            
            response = self.client.audio.transcriptions.create(
                model=settings.GROQ_STT_MODEL,
                file=audio_file,
            )
            
            return {
                "transcript": response.text,
                "language": getattr(response, 'language', 'en'),
                "confidence": 0.95,
            }
        except Exception as e:
            return {
                "transcript": "",
                "language": "en",
                "confidence": 0,
                "error": str(e),
            }
