from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..routers.auth import get_current_user
from ..models.models import User
from ..providers.speech_to_text import SpeechToTextProvider

router = APIRouter(prefix="/api/speech", tags=["speech"])

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
