from __future__ import annotations

import base64
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
MAX_RECORD_AGE_DAYS = 365


def _normalize_webui_url(base_url: str, webui_path: Any) -> str:
    if not isinstance(webui_path, str) or not webui_path.strip():
        return ""

    if webui_path.startswith("http://") or webui_path.startswith("https://"):
        return webui_path

    return f"{base_url.rstrip('/')}/{webui_path.lstrip('/')}"


def _updated_at_sort_key(value: Any) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)

    try:
        normalized = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=timezone.utc)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed


class ConfluenceService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def fetch_pages(
        self,
        limit: int = 200,
        since: str | None = None,
        created_since: str | None = None,
    ) -> list[dict[str, Any]]:
        if (
            not self.settings.confluence_email
            or not self.settings.confluence_api_token
            or not self.settings.confluence_base_url
        ):
            logger.warning("Confluence credentials are not configured")
            return []

        endpoint = f"{self.settings.confluence_base_url}/rest/api/content/search"
        space_filters = [
            f'space = "{space}"' for space in self.settings.confluence_space_keys
        ]

        cql_parts = ["type = page"]

        # Add space filters
        if space_filters:
            cql_parts.append(f"({' OR '.join(space_filters)})")

        # Add time filters for incremental sync
        time_filters = []
        if since:
            time_filters.append(f'lastmodified >= "{since}"')
        if created_since:
            time_filters.append(f'created >= "{created_since}"')

        if time_filters:
            # Use OR to get pages that are either new OR updated
            cql_parts.append(f"({' OR '.join(time_filters)})")

        cql = " AND ".join(cql_parts)

        # Add ordering to get most recently updated pages first
        cql += " ORDER BY lastmodified DESC"

        logger.info(
            "Confluence fetch starting base_url=%s spaces=%s limit=%s cql=%s",
            self.settings.confluence_base_url,
            self.settings.confluence_space_keys,
            limit,
            cql,
        )

        auth_value = (
            f"{self.settings.confluence_email}:{self.settings.confluence_api_token}"
        )
        encoded_auth = base64.b64encode(auth_value.encode("utf-8")).decode("utf-8")
        headers = {
            "Authorization": f"Basic {encoded_auth}",
            "Accept": "application/json",
        }
        pages: list[dict[str, Any]] = []
        raw_results_count = 0
        stale_count = 0
        start = 0
        page_size = min(limit, 200)

        async with httpx.AsyncClient(timeout=20.0) as client:
            while len(pages) < limit:
                params = {
                    "cql": cql,
                    "limit": page_size,
                    "start": start,
                    "expand": "version,history,space,body.storage",
                }

                try:
                    response = await client.get(
                        endpoint, headers=headers, params=params
                    )
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    logger.error(
                        "Confluence API error: status=%s url=%s response=%s",
                        e.response.status_code,
                        str(e.request.url),
                        e.response.text,
                    )
                    raise
                except Exception as e:
                    logger.error("Confluence request failed: %s", str(e))
                    raise

                payload = response.json()

                results = payload.get("results", [])
                raw_results_count += len(results)
                logger.info(
                    "Confluence fetch page status=%s start=%s page_results=%s accumulated_raw=%s",
                    response.status_code,
                    start,
                    len(results),
                    raw_results_count,
                )

                if not results:
                    break

                for item in results:
                    updated_at = (item.get("version") or {}).get("when")
                    # No age filtering - all pages from configured spaces are relevant

                    pages.append(
                        {
                            "id": str(item.get("id", "")),
                            "title": item.get("title", ""),
                            "excerpt": item.get("excerpt", ""),
                            "content": (item.get("body") or {})
                            .get("storage", {})
                            .get("value", ""),
                            "space_key": (item.get("space") or {}).get("key", ""),
                            "url": _normalize_webui_url(
                                self.settings.confluence_base_url,
                                item.get("_links", {}).get("webui", ""),
                            ),
                            "author_name": (item.get("history") or {})
                            .get("createdBy", {})
                            .get("displayName", ""),
                            "updated_at": updated_at,
                        }
                    )
                    if len(pages) >= limit:
                        break

                if len(results) < page_size:
                    break

                start += len(results)

        logger.info(
            "Confluence fetch completed raw_results=%s requested_limit=%s returned_fresh_pages=%s stale_pages=%s",
            raw_results_count,
            limit,
            len(pages),
            stale_count,
        )

        logger.info(
            "Confluence fetch filtered fresh_pages=%s stale_pages=%s",
            len(pages),
            stale_count,
        )

        pages.sort(
            key=lambda page: _updated_at_sort_key(page.get("updated_at")), reverse=True
        )

        return pages
