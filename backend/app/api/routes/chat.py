from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models.aha_feature import AhaFeature
from app.models.chat import ChatMessage, ChatSession
from app.models.confluence_page import ConfluencePage
from app.services.chatbot_service import ChatbotService

router = APIRouter()
service = ChatbotService()


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: UUID | None = None
    story_id: UUID | None = None
    context_title: str | None = Field(default=None, max_length=200)
    context_hint: str | None = Field(default=None, max_length=500)


class ContextRequest(BaseModel):
    story_id: UUID


class IdeaRequest(BaseModel):
    rough_idea: str = Field(min_length=10, max_length=5000)
    story_id: UUID | None = None


@router.post("/message")
async def post_chat_message(
    payload: ChatMessageRequest,
    db: Session = Depends(get_db_session),
) -> dict:
    session_id = str(payload.session_id) if payload.session_id else str(uuid4())

    chat_session = db.get(ChatSession, session_id)
    if chat_session is None:
        chat_session = ChatSession(
            id=session_id,
            session_name=payload.message[:80],
            focused_story_id=str(payload.story_id) if payload.story_id else None,
        )
        db.add(chat_session)

    user_message = ChatMessage(
        id=str(uuid4()),
        session_id=session_id,
        role="user",
        content=payload.message,
    )
    db.add(user_message)

    response = await service.ask(
        payload.message,
        context_title=payload.context_title,
        context_hint=payload.context_hint,
    )
    assistant_message = ChatMessage(
        id=str(uuid4()),
        session_id=session_id,
        role="assistant",
        content=response.get("answer", ""),
    )
    db.add(assistant_message)
    db.commit()

    return {
        "session_id": session_id,
        "answer": response.get("answer", ""),
        "sources": response.get("sources", []),
    }


@router.get("/sessions")
async def get_chat_sessions(db: Session = Depends(get_db_session)) -> dict:
    query = select(ChatSession).order_by(desc(ChatSession.created_at)).limit(100)
    result = db.execute(query)
    sessions = result.scalars().all()

    items: list[dict] = []
    for session in sessions:
        messages_query = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at)
        )
        messages_result = db.execute(messages_query)
        messages = messages_result.scalars().all()
        latest_message = messages[-1].content if messages else ""

        items.append(
            {
                "session_name": session.session_name,
                "created_at": session.created_at.isoformat()
                if session.created_at
                else None,
                "message_count": len(messages),
                "latest_message": latest_message,
            }
        )

    return {"items": items}


@router.get("/sessions/{session_id}")
async def get_chat_session(
    session_id: UUID,
    db: Session = Depends(get_db_session),
) -> dict:
    session_key = str(session_id)
    session = db.get(ChatSession, session_key)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    query = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_key)
        .order_by(ChatMessage.created_at)
    )
    result = db.execute(query)
    messages = result.scalars().all()

    return {
        "session_name": session.session_name,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "messages": [
            {
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at.isoformat()
                if message.created_at
                else None,
            }
            for message in messages
        ],
    }


@router.get("/suggestions")
async def get_chat_suggestions(
    limit: int = Query(default=5, ge=1, le=10),
    db: Session = Depends(get_db_session),
) -> dict:
    pages = (
        db.execute(
            select(ConfluencePage.title)
            .order_by(desc(ConfluencePage.updated_at))
            .limit(3)
        )
        .scalars()
        .all()
    )
    ideas = db.execute(
        select(AhaFeature.name, AhaFeature.reference_num)
        .order_by(desc(AhaFeature.updated_at))
        .limit(3)
    ).all()

    suggestions: list[str] = []
    for title in pages[:2]:
        if title:
            suggestions.append(f"Tell me about: {title}")
    for name, ref in ideas[:2]:
        if name:
            short = name[:55] + "…" if len(name) > 55 else name
            suggestions.append(f"What's the status of {ref}: {short}?")

    fallbacks = [
        "How does the consent receipt pipeline work?",
        "What Cosmos DB containers store consent data?",
        "How does Kafka route consent events?",
        "What APIs are used for data subject deletion?",
        "Explain Linked Identity Groups",
    ]
    for fb in fallbacks:
        if len(suggestions) >= limit:
            break
        suggestions.append(fb)

    return {"suggestions": suggestions[:limit]}


@router.post("/context")
async def post_chat_context(_: ContextRequest) -> dict:
    return {"story": None, "related_pages": [], "related_stories": []}


@router.post("/formulate-idea")
async def post_formulate_idea(payload: IdeaRequest) -> dict:
    return {
        "problem_statement": payload.rough_idea,
        "structured_idea": "Idea formulation service will be implemented in phase 5.",
        "suggested_approach": "",
        "questions_to_consider": [],
    }


@router.get("/related/{story_id}")
async def get_related(story_id: UUID, limit: int = 10) -> dict:
    return {"story_id": str(story_id), "limit": limit, "items": []}
