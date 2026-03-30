from fastapi import APIRouter

from app.api.routes import (
    aha,
    analysis,
    chat,
    confluence,
    consent_flow,
    cosmos,
    embeddings,
    health,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(confluence.router, prefix="/confluence", tags=["confluence"])
api_router.include_router(aha.router, prefix="/aha", tags=["aha"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(cosmos.router, prefix="/cosmos", tags=["cosmos"])
api_router.include_router(embeddings.router, prefix="/embeddings", tags=["embeddings"])
api_router.include_router(
    consent_flow.router, prefix="/consent-flow", tags=["consent-flow"]
)
