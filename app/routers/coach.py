from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_ai
from app.models import User
from app.schemas import CoachChatIn, CoachChatOut, ConversationDetail, ConversationOut, MessageOut
from app.services import coach_service

router = APIRouter(prefix="/api/coach", tags=["coach"])


@router.post("/chat", response_model=CoachChatOut)
def chat(body: CoachChatIn, user: User = Depends(require_ai), db: Session = Depends(get_db)):
    """Ask the coach. conversation_id null starts a new chat. Needs AI turned on."""
    conversation_id, mode, reply = coach_service.chat(db, user, body.conversation_id, body.message)
    return CoachChatOut(
        conversation_id=conversation_id, mode=mode, message=MessageOut.model_validate(reply)
    )


# Reading and deleting saved chats works even with AI turned off, so users can always remove their data.

@router.get("/conversations", response_model=list[ConversationOut])
def conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return coach_service.list_conversations(db, user)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def conversation(
    conversation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return coach_service.get_conversation(db, user, conversation_id)


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    coach_service.delete_conversation(db, user, conversation_id)
