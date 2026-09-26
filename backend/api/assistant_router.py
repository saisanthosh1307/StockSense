from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.user import User
from backend.services.auth_service import get_current_user
from backend.services.assistant_service import AssistantService

router = APIRouter(prefix="/assistant", tags=["AI Inventory Assistant"])

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
def chat_with_assistant(
    req: ChatRequest,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return AssistantService.process_query(
        db=db,
        query_text=req.message,
        user_id=current_user.id if current_user else None
    )
