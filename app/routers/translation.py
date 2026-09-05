from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from ..core.database import get_db
from ..routers.auth import get_current_user
from ..models.models import User
from ..providers.translation import TranslationProvider

router = APIRouter(prefix="/api/translate", tags=["translation"])

@router.post("")
async def translate_text(
    text: str = Form(...),
    target_language: str = Form(...),
    source_language: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
):
    try:
        provider = TranslationProvider()
        result = await provider.translate(
            text=text,
            target_language=target_language,
            source_language=source_language,
        )
        
        return {
            "success": True,
            "translated_text": result["translated_text"],
            "source_language": result.get("source_language"),
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "TRANSLATION_FAILED",
                "message": str(e),
            },
        }
