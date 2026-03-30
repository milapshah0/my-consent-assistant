from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models.aha_feature import AhaFeature
from app.services.aha_service import _categorize_feature
from app.tasks.sync_aha import sync_aha_features

router = APIRouter()


@router.get("/categories")
async def get_aha_categories(db: Session = Depends(get_db_session)) -> dict:
    rows = db.execute(select(AhaFeature.name, AhaFeature.description)).all()
    seen: set[str] = set()
    for name, description in rows:
        cat = _categorize_feature(name or "", description or "")
        seen.add(cat)
    return {"categories": sorted(seen)}


@router.get("/ideas")
async def get_aha_ideas(
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    category: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db_session),
) -> dict:
    query = select(AhaFeature)
    if status:
        query = query.where(AhaFeature.status.ilike(status))
    if priority:
        query = query.where(AhaFeature.priority.ilike(priority))

    all_rows = db.execute(query.order_by(desc(AhaFeature.updated_at))).scalars().all()

    items = [
        {
            "id": feature.id,
            "reference_num": feature.reference_num,
            "name": feature.name,
            "description": feature.description,
            "status": feature.status,
            "priority": feature.priority,
            "category": _categorize_feature(feature.name, feature.description or ""),
            "url": feature.url,
        }
        for feature in all_rows
    ]

    if category:
        items = [item for item in items if item["category"].lower() == category.lower()]

    total = len(items)
    page_items = items[offset : offset + limit]

    return {
        "items": page_items,
        "meta": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_more": offset + limit < total,
        },
    }


@router.post("/sync")
async def sync_aha() -> dict:
    await sync_aha_features()
    return {"status": "ok"}


@router.get("/ideas/{idea_id}")
async def get_aha_idea(idea_id: str, db: Session = Depends(get_db_session)) -> dict:
    feature = db.get(AhaFeature, idea_id)
    if feature is None:
        return {"id": idea_id, "name": "", "description": ""}
    return {
        "id": feature.id,
        "reference_num": feature.reference_num,
        "name": feature.name,
        "description": feature.description,
        "status": feature.status,
        "priority": feature.priority,
        "category": _categorize_feature(feature.name, feature.description or ""),
        "url": feature.url,
    }
