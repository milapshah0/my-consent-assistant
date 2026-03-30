from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import SessionLocal
from app.models.aha_feature import AhaFeature
from app.models.confluence_page import ConfluencePage


class AnalysisService:
    async def summary(self, days: int = 7) -> dict:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        with SessionLocal() as db:
            pages = db.execute(select(ConfluencePage)).scalars().all()
            features = db.execute(select(AhaFeature)).scalars().all()

        recent_updates = sum(
            1
            for item in [*pages, *features]
            if item.updated_at and item.updated_at >= cutoff
        )

        token_counter: Counter[str] = Counter()
        for page in pages:
            token_counter.update(self._extract_tokens(page.title))
        for feature in features:
            token_counter.update(self._extract_tokens(feature.name))

        top_keywords = [
            {"keyword": token, "count": count}
            for token, count in token_counter.most_common(10)
            if len(token) > 2
        ]

        activity_trend = [
            {"label": "confluence_pages", "value": len(pages)},
            {"label": "aha_features", "value": len(features)},
        ]

        return {
            "days": days,
            "total_pages": len(pages),
            "total_features": len(features),
            "recent_updates": recent_updates,
            "top_keywords": top_keywords,
            "activity_trend": activity_trend,
        }

    @staticmethod
    def _extract_tokens(text: str) -> list[str]:
        normalized = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
        return [token for token in normalized.split() if token]
