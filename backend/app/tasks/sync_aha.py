import logging
from datetime import date, datetime

from sqlalchemy import select

from app.database import SessionLocal
from app.models.aha_feature import AhaFeature
from app.services.aha_service import AhaService

logger = logging.getLogger(__name__)


async def sync_aha_features() -> None:
    logger.info("sync_aha_features started")
    service = AhaService()
    fetched_features = await service.fetch_ideas(limit=200)

    idea_ids = [str(f.get("id", "")) for f in fetched_features if f.get("id")]

    inserted = 0
    updated = 0
    skipped = 0

    with SessionLocal() as db:
        existing_map: dict[str, AhaFeature] = {}
        if idea_ids:
            query = select(AhaFeature).where(AhaFeature.id.in_(idea_ids))
            existing_rows = db.execute(query).scalars().all()
            existing_map = {row.id: row for row in existing_rows}

        for feature in fetched_features:
            feature_id = str(feature.get("id", ""))
            if not feature_id:
                continue

            existing = existing_map.get(feature_id)
            reference_num = str(feature.get("reference_num", ""))
            name = str(feature.get("name", ""))
            description = str(feature.get("description", ""))
            status = str(feature.get("status", "Not started"))
            priority = str(feature.get("priority", "Medium"))
            url = str(feature.get("url", ""))
            due_date_str = feature.get("due_date")
            due_date: date | None = None
            if due_date_str:
                try:
                    due_date = datetime.fromisoformat(str(due_date_str)).date()
                except (ValueError, TypeError):
                    pass

            if existing is None:
                db.add(
                    AhaFeature(
                        id=feature_id,
                        reference_num=reference_num,
                        name=name,
                        description=description,
                        status=status,
                        priority=priority,
                        due_date=due_date,
                        url=url,
                    )
                )
                inserted += 1
                continue

            if (
                existing.reference_num == reference_num
                and existing.name == name
                and existing.description == description
                and existing.status == status
                and existing.priority == priority
                and existing.due_date == due_date
                and existing.url == url
            ):
                skipped += 1
                continue

            existing.reference_num = reference_num
            existing.name = name
            existing.description = description
            existing.status = status
            existing.priority = priority
            existing.due_date = due_date
            existing.url = url
            updated += 1

        db.commit()

    logger.info(
        "sync_aha_features fetched=%s inserted=%s updated=%s skipped=%s",
        len(fetched_features),
        inserted,
        updated,
        skipped,
    )
    logger.info("sync_aha_features finished")
