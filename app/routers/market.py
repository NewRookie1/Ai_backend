from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..routers.auth import get_current_user
from ..models.models import User
from ..providers.market import MarketProvider

router = APIRouter(prefix="/api/market", tags=["market"])

@router.get("/analysis")
async def get_market_analysis(
    category: str,
    current_user: User = Depends(get_current_user),
):
    try:
        provider = MarketProvider()
        result = await provider.get_analysis(category)
        
        return {
            "success": True,
            "data": result,
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "MARKET_FAILED",
                "message": str(e),
            },
        }

@router.get("/trends")
async def get_market_trends(
    current_user: User = Depends(get_current_user),
):
    try:
        provider = MarketProvider()
        result = await provider.get_trends()
        
        return {
            "success": True,
            "data": result,
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "TRENDS_FAILED",
                "message": str(e),
            },
        }

@router.get("/trending")
async def get_trending_products(
    current_user: User = Depends(get_current_user),
):
    try:
        provider = MarketProvider()
        result = await provider.get_trending()
        
        return {
            "success": True,
            "data": result,
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "TRENDING_FAILED",
                "message": str(e),
            },
        }
