from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models.confluence_page import ConfluencePage
from app.tasks.sync_confluence import sync_confluence_pages

router = APIRouter()


@router.get("/pages")
async def get_confluence_pages(
    search: str | None = Query(default=None),
    space: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db_session),
) -> dict:
    query = select(ConfluencePage)
    if search:
        query = query.where(ConfluencePage.title.ilike(f"%{search}%"))
    if space:
        query = query.where(ConfluencePage.space_key.ilike(space))

    rows = db.execute(query.order_by(desc(ConfluencePage.updated_at))).scalars().all()
    paginated = rows[offset : offset + limit]
    return {
        "items": [
            {
                "id": page.id,
                "title": page.title,
                "excerpt": page.excerpt,
                "space_key": page.space_key,
                "url": page.url,
                "author_name": page.author_name,
                "updated_at": page.updated_at.isoformat() if page.updated_at else None,
            }
            for page in paginated
        ],
        "meta": {
            "search": search,
            "space": space,
            "limit": limit,
            "offset": offset,
            "total": len(rows),
        },
    }


@router.get("/pages/{page_id}")
async def get_confluence_page(
    page_id: str, db: Session = Depends(get_db_session)
) -> dict:
    page = db.get(ConfluencePage, page_id)
    if page is None:
        return {"id": page_id, "title": "", "content": ""}
    return {
        "id": page.id,
        "title": page.title,
        "excerpt": page.excerpt,
        "content": page.content,
        "space_key": page.space_key,
        "url": page.url,
        "author_name": page.author_name,
        "updated_at": page.updated_at.isoformat() if page.updated_at else None,
    }


@router.post("/sync")
async def trigger_confluence_sync(
    force: bool = Query(
        default=False, description="Force sync regardless of time window"
    ),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> dict:
    """
    Trigger a manual sync of Confluence pages.

    - **force=False**: Respects 12-hour minimum interval between syncs
    - **force=True**: Immediate sync regardless of last sync time

    The sync uses CQL to efficiently fetch:
    - New pages created since last sync
    - Existing pages updated since last sync
    - Pages from configured spaces only
    """
    background_tasks.add_task(sync_confluence_pages, force=force)
    return {
        "message": f"Confluence sync triggered (force={force})",
        "force": force,
        "details": {
            "incremental_sync": not force,
            "cql_filters": [
                "type = page",
                "space filters",
                "(lastmodified >= timestamp OR created >= timestamp)",
            ],
            "min_interval_hours": 12,
        },
    }


@router.get("/spaces")
async def get_confluence_spaces(db: Session = Depends(get_db_session)) -> dict:
    query = select(ConfluencePage.space_key).where(ConfluencePage.space_key != "")
    rows = db.execute(query).all()
    spaces = sorted({row[0] for row in rows if row[0]})
    return {"items": spaces}
