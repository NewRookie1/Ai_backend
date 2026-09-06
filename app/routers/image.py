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

@router.post("/classify")
async def classify_image(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """MobileCLIP-S0 ONNX zero-shot classification. Returns just the label.

    Labels (== dataset/ folders): bamboo_basket, pottery,
    textile, wooden_craft. No retraining needed to add products — just
    extend ARTISAN_LABELS / LABEL_PROMPTS in mobileclip_classifier.py.
    Response envelope matches other endpoints; the label itself is at
    data.label so ApiResponse parsing keeps working.
    """
    try:
        from ..services.mobileclip_classifier import predict_with_scores
        image_content = await image.read()
        label, confidence, scores = predict_with_scores(image_content)
        return {
            "success": True,
            "data": {"label": label, "confidence": confidence, "scores": scores},
        }
    except Exception as e:
        return {"success": False, "error": {"code": "CLASSIFY_FAILED", "message": str(e)}}

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
