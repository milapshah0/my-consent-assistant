import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models.confluence_page import ConfluencePage
from app.services.confluence_service import ConfluenceService

logger = logging.getLogger(__name__)

MIN_SYNC_INTERVAL_HOURS = 12
settings = get_settings()


async def sync_confluence_pages(force: bool = False) -> None:
    logger.info("sync_confluence_pages started force=%s", force)

    service = ConfluenceService()

    # Simple logic: force sync gets everything, regular sync gets recent updates
    if force:
        # Force sync: get ALL pages without time filtering
        logger.info("sync_confluence_pages performing force sync - getting ALL pages")
        fetched_pages = await service.fetch_pages(limit=5000)
    else:
        # Regular sync: get pages updated in last 24 hours
        logger.info(
            "sync_confluence_pages performing regular sync - getting recent updates"
        )
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        cutoff_str = cutoff_time.strftime("%Y-%m-%d %H:%M")
        fetched_pages = await service.fetch_pages(
            limit=5000,
            since=cutoff_str,
            created_since=cutoff_str,
        )
    logger.info(
        "sync_confluence_pages fetched_pages=%s configured_spaces=%s",
        len(fetched_pages),
        settings.confluence_space_keys,
    )

    # All pages from configured spaces are relevant - no filtering needed
    relevant_pages = fetched_pages
    logger.info(
        "sync_confluence_pages processing_pages=%s",
        len(relevant_pages),
    )
    page_ids = [str(page.get("id", "")) for page in relevant_pages if page.get("id")]

    inserted = 0
    updated = 0
    skipped = 0

    with SessionLocal() as db:
        existing_map: dict[str, ConfluencePage] = {}
        if page_ids:
            query = select(ConfluencePage).where(ConfluencePage.id.in_(page_ids))
            existing_rows = db.execute(query).scalars().all()
            existing_map = {row.id: row for row in existing_rows}

        for page in relevant_pages:
            page_id = str(page.get("id", ""))
            if not page_id:
                continue

            existing = existing_map.get(page_id)
            title = str(page.get("title", ""))
            excerpt = str(page.get("excerpt", ""))
            content = str(page.get("content", ""))  # Get actual content
            space_key = str(page.get("space_key", ""))
            url = str(page.get("url", ""))
            author_name = str(page.get("author_name", ""))
            updated_at = page.get("updated_at")  # Get actual Confluence updated_at

            if existing is None:
                db.add(
                    ConfluencePage(
                        id=page_id,
                        title=title,
                        excerpt=excerpt,
                        content=content,  # Store actual content
                        space_key=space_key,
                        url=url,
                        author_name=author_name,
                        updated_at=updated_at,  # Store actual timestamp
                    )
                )
                inserted += 1
                continue

            if (
                existing.title == title
                and existing.excerpt == excerpt
                and existing.content == content  # Check content too
                and existing.space_key == space_key
                and existing.url == url
                and existing.author_name == author_name
            ):
                skipped += 1
                continue

            existing.title = title
            existing.excerpt = excerpt
            existing.content = content  # Update content
            existing.space_key = space_key
            existing.url = url
            existing.author_name = author_name
            existing.updated_at = updated_at  # Update with actual timestamp
            existing.synced_at = datetime.now(timezone.utc)
            updated += 1

        db.commit()

    logger.info(
        "sync_confluence_pages fetched=%s relevant=%s inserted=%s updated=%s skipped=%s force=%s",
        len(fetched_pages),
        len(relevant_pages),
        inserted,
        updated,
        skipped,
        force,
    )
    logger.info("sync_confluence_pages finished")
