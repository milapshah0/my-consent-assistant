from fastapi import APIRouter, Query

from app.services.analysis_service import AnalysisService

router = APIRouter()

service = AnalysisService()


@router.get("/summary")
async def get_analysis_summary(days: int = Query(default=7, ge=1, le=90)) -> dict:
    return await service.summary(days=days)


@router.get("/keywords")
async def get_analysis_keywords() -> dict:
    return {"items": []}


@router.get("/trends")
async def get_analysis_trends() -> dict:
    return {"items": []}
