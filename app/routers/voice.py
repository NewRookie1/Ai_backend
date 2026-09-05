from fastapi import APIRouter, Depends, UploadFile, File, Form, Body
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from ..core.database import get_db
from ..routers.auth import get_current_user
from ..models.models import User
from ..providers.agent import AgentProvider

router = APIRouter(prefix="/api", tags=["agent"])

class TextRequest(BaseModel):
    text: str
    current_screen: Optional[str] = None
    conversation_id: Optional[str] = None
    user_language: Optional[str] = "en"
    image_path: Optional[str] = None

@router.post("/voice-chat")
async def voice_chat(
    audio: UploadFile = File(...),
    current_screen: Optional[str] = Form(None),
    conversation_id: Optional[str] = Form(None),
    user_language: Optional[str] = Form("en"),
    image_path: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        audio_content = await audio.read()
        
        agent = AgentProvider()
        result = await agent.process_voice(
            audio_content=audio_content,
            filename=audio.filename,
            user_id=str(current_user.id),
            current_screen=current_screen,
            conversation_id=conversation_id,
            user_language=user_language,
            image_path=image_path,
            db=db,
        )
        
        return {
            "success": True,
            **result,
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "AGENT_FAILED",
                "message": str(e),
            },
        }

@router.post("/agent/execute")
async def execute_agent(
    request: TextRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        agent = AgentProvider()
        result = await agent.process_text(
            text=request.text,
            user_id=str(current_user.id),
            current_screen=request.current_screen,
            conversation_id=request.conversation_id,
            user_language=request.user_language,
            image_path=request.image_path,
            db=db,
        )
        
        return {
            "success": True,
            **result,
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "AGENT_FAILED",
                "message": str(e),
            },
        }

@router.post("/agent/execute/tool")
async def execute_tool(
    tool: str,
    parameters: dict = {},
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        from ..agent.tools import ToolRegistry
        registry = ToolRegistry()
        result = await registry.execute(tool, parameters, str(current_user.id), db)
        
        return {
            "success": True,
            "data": result,
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "TOOL_FAILED",
                "message": str(e),
            },
        }
