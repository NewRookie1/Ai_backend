from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
import io
from ..core.database import get_db
from ..routers.auth import get_current_user
from ..models.models import User
from ..providers.speech_to_text import SpeechToTextProvider

router = APIRouter(prefix="/api/speech", tags=["speech"])

# Preferred neural voices per app language (soft female where known).
TTS_VOICES = {
    "en": "en-US-AriaNeural",
    "hi": "hi-IN-SwaraNeural",
    "mr": "mr-IN-AarohiNeural",
    "gu": "gu-IN-DhwaniNeural",
    "bn": "bn-IN-TanishaaNeural",
    "ta": "ta-IN-PallaviNeural",
    "te": "te-IN-ShrutiNeural",
    "kn": "kn-IN-SapnaNeural",
    "ml": "ml-IN-SobhanaNeural",
    "pa": "pa-IN-NeerjaNeural",
}

class SpeakRequest(BaseModel):
    text: str
    language: Optional[str] = "en"

@router.post("/speak")
async def speak_text(payload: SpeakRequest):
    """In-app voice: server renders speech audio so the app NEVER depends
    on the device's system TTS engine (many BlueStacks images have none).
    Public endpoint (no auth) so Demo Mode also speaks."""
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")
    # Keep replies short for voice; truncate abusive lengths.
    if len(text) > 600:
        text = text[:600]
    lang = (payload.language or "en").lower()
    voice = TTS_VOICES.get(lang, TTS_VOICES["en"])
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice, rate="-5%", pitch="+2Hz")
        audio = b"".join(
            chunk["audio"] async for chunk in communicate.stream()
            if chunk["type"] == "audio"
        )
        if not audio:
            raise RuntimeError("empty audio")
        return StreamingResponse(io.BytesIO(audio), media_type="audio/mpeg")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"TTS failed: {e}")

@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    try:
        audio_content = await audio.read()
        
        if len(audio_content) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")
        
        provider = SpeechToTextProvider()
        result = await provider.transcribe(audio_content, audio.filename)
        
        return {
            "success": True,
            "transcript": result["transcript"],
            "detected_language": result["language"],
            "confidence": result["confidence"],
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "STT_FAILED",
                "message": str(e),
            },
        }
