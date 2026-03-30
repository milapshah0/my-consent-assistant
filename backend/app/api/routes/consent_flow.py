from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.consent_flow_service import ConsentFlowService

router = APIRouter()
_service = ConsentFlowService()


@router.get("/sections")
async def get_consent_flow_sections() -> dict:
    sections = _service.get_sections()
    return {
        "items": [
            {
                "id": s["id"],
                "title": s["title"],
                "content": s["content"],
                "level": s["level"],
                "service": s["service"],
                "phase": s["phase"],
                "excerpt": s["content"][:220].rstrip() + ("..." if len(s["content"]) > 220 else ""),
            }
            for s in sections
        ]
    }


class ConsentFlowAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    section_id: str | None = None


@router.post("/ask")
async def ask_consent_flow(payload: ConsentFlowAskRequest) -> dict:
    return await _service.ask(payload.question, section_id=payload.section_id)


@router.post("/index")
async def index_consent_flow() -> dict:
    return await _service.index_sections()
