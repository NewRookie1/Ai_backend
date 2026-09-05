from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from ..core.database import get_db
from ..routers.auth import get_current_user
from ..models.models import User
from ..providers.vision import VisionProvider

router = APIRouter(prefix="/api/image", tags=["image"])

@router.post("/analyze")
async def analyze_image(
    image: UploadFile = File(...),
    purpose: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
):
    try:
        image_content = await image.read()
        
        provider = VisionProvider()
        result = await provider.analyze(
            image_content=image_content,
            filename=image.filename,
            purpose=purpose,
        )
        
        return {
            "success": True,
            "data": result,
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "VISION_FAILED",
                "message": str(e),
            },
        }

@router.post("/enhance")
async def enhance_image(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    try:
        image_content = await image.read()
        
        provider = VisionProvider()
        result = await provider.enhance(image_content=image_content)
        
        return {
            "success": True,
            "data": result,
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "ENHANCE_FAILED",
                "message": str(e),
            },
        }
