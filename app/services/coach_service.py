"""AI coach: conversations, saved messages, and the habit context sent with each question.

generate_reply() is the one place the RAG plugs in later. Everything around it
(conversations, saved messages, the user's habit and risk summary) already works.
"""
from datetime import date, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ChatMessage, Conversation, User, utcnow
from app.services import risk_service
from app.services.data import load_user_data, today_for
from ml.features import streak
from ml.predict import ModelNotReady


def build_context(db: Session, user: User, today: Optional[date] = None) -> dict:
    """What the coach knows about the user: each habit with its recent activity and risk."""
    habits, completions = load_user_data(db, user.id)
    as_of = today_for(user, today) - timedelta(days=1)
    try:
        risk_by_id = {r["habit_id"]: r for r in risk_service.compute_risk(db, user, today)}
    except ModelNotReady:
        risk_by_id = {}

    out = []
    for h in habits:
        done = completions.get(h.id, set())
        r = risk_by_id.get(h.id)
        out.append(
            {
                "id": h.id,
                "name": h.name,
                "done_last_7": sum(1 for i in range(7) if as_of - timedelta(days=i) in done),
                "done_last_30": sum(1 for i in range(30) if as_of - timedelta(days=i) in done),
                "streak": streak(done, as_of),
                "risk": r["risk"] if r else None,
                "level": r["level"] if r else None,
                "reasons": r["reasons"] if r else [],
            }
        )
    return {"as_of": as_of.isoformat(), "habits": out}


def generate_reply(question: str, context: dict) -> tuple[str, list[dict], str]:
    """TODO(RAG): replace this body with retrieval over the knowledge notes + an LLM call.

    Must return (answer text, [{"id": note_id, "title": note_title}, ...], mode),
    where mode is "llm" or "retrieval_only".
    """
    at_risk = [h for h in context.get("habits", []) if h.get("level") in ("medium", "high")]
    if at_risk:
        names = ", ".join(f"{h['name']} ({round(h['risk'] * 100)}%)" for h in at_risk)
        text = f"The AI coach is not connected yet. For now, these habits look at risk: {names}."
    else:
        text = "The AI coach is not connected yet. None of your habits currently look at risk."
    return text, [], "placeholder"


def get_conversation(db: Session, user: User, conversation_id: str) -> Conversation:
    conv = db.get(Conversation, conversation_id)
    if conv is None or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


def list_conversations(db: Session, user: User) -> list[Conversation]:
    return list(
        db.scalars(
            select(Conversation)
            .where(Conversation.user_id == user.id)
            .order_by(Conversation.updated_at.desc())
        )
    )


def delete_conversation(db: Session, user: User, conversation_id: str) -> None:
    conv = get_conversation(db, user, conversation_id)
    db.delete(conv)
    db.commit()


def chat(db: Session, user: User, conversation_id: Optional[str], message: str):
    """Save the question, build the habit context, get a reply, save it. Returns (conv id, mode, reply)."""
    context = build_context(db, user)

    if conversation_id is None:
        conv = Conversation(user_id=user.id, title=message[:60] or "New chat")
        db.add(conv)
        db.flush()  # assigns conv.id
    else:
        conv = get_conversation(db, user, conversation_id)

    db.add(ChatMessage(conversation_id=conv.id, role="user", content=message))
    answer, sources, mode = generate_reply(message, context)
    reply = ChatMessage(
        conversation_id=conv.id, role="assistant", content=answer, sources=sources, context=context
    )
    db.add(reply)
    conv.updated_at = utcnow()
    db.commit()
    db.refresh(reply)
    return conv.id, mode, reply
