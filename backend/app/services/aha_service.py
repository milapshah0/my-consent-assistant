from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import httpx

from app.config import get_settings
from app.services.azure_openai_service import AzureOpenAIService

logger = logging.getLogger(__name__)
MAX_RECORD_AGE_DAYS = 365

STATIC_CATEGORIES = [
    "Performance",
    "Data Pipeline",
    "Storage & Database",
    "Consent API",
    "Reporting & Audit",
    "Identity & DSR",
    "Preference Center",
    "Cookie & Consent String",
    "Privacy Notices",
    "Integration & SDK",
]

DYNAMIC_CATEGORIES_FILE = (
    Path(__file__).parent.parent.parent.parent / "docs" / "aha_categories.json"
)


def _load_dynamic_categories() -> dict[str, list[str]]:
    try:
        if DYNAMIC_CATEGORIES_FILE.exists():
            return json.loads(DYNAMIC_CATEGORIES_FILE.read_text())
    except Exception:
        pass
    return {}


def _save_dynamic_categories(categories: dict[str, list[str]]) -> None:
    try:
        DYNAMIC_CATEGORIES_FILE.parent.mkdir(parents=True, exist_ok=True)
        DYNAMIC_CATEGORIES_FILE.write_text(json.dumps(categories, indent=2))
    except Exception as exc:
        logger.warning("Failed to save dynamic categories: %s", exc)


def _extract_seed_keywords(name: str, description: str) -> list[str]:
    _STOPWORDS = {
        "with",
        "that",
        "this",
        "from",
        "have",
        "will",
        "when",
        "what",
        "where",
        "which",
        "their",
        "into",
        "them",
        "then",
        "been",
        "does",
        "only",
        "each",
        "more",
        "also",
        "very",
        "most",
        "some",
        "such",
        "both",
        "even",
        "back",
        "good",
        "know",
        "take",
        "just",
        "over",
        "like",
        "through",
        "after",
        "during",
        "should",
        "could",
        "would",
        "these",
        "those",
        "other",
        "about",
        "there",
        "being",
        "using",
        "across",
        "based",
        "data",
        "user",
        "allow",
        "make",
        "need",
        "able",
        "provide",
        "include",
        "ensure",
        "support",
        "return",
        "current",
    }
    words = re.findall(r"\b[a-z]{4,}\b", f"{name} {description}".lower())
    seen: set[str] = set()
    result: list[str] = []
    for word in words:
        if word not in _STOPWORDS and word not in seen:
            seen.add(word)
            result.append(word)
            if len(result) >= 6:
                break
    return result


class _HtmlToText(HTMLParser):
    _BLOCK_TAGS = {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}
    _LIST_ITEM_TAGS = {"li"}
    _SKIP_TAGS = {"style", "script"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._in_skip = False
        self._pending_bullet = False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        tag = tag.lower()
        if tag in self._SKIP_TAGS:
            self._in_skip = True
        elif tag in self._BLOCK_TAGS:
            self._parts.append("\n")
        elif tag in self._LIST_ITEM_TAGS:
            self._parts.append("\n- ")
            self._pending_bullet = True

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self._SKIP_TAGS:
            self._in_skip = False

    def handle_data(self, data: str) -> None:
        if not self._in_skip:
            self._parts.append(data)

    def get_text(self) -> str:
        raw = "".join(self._parts)
        lines = [line.rstrip() for line in raw.splitlines()]
        cleaned: list[str] = []
        prev_blank = False
        for line in lines:
            is_blank = line == ""
            if is_blank and prev_blank:
                continue
            cleaned.append(line)
            prev_blank = is_blank
        return "\n".join(cleaned).strip()


def _html_to_text(html: str) -> str:
    if not html or not html.strip():
        return ""
    if not re.search(r"<[a-zA-Z]", html):
        return html.strip()
    parser = _HtmlToText()
    parser.feed(html)
    return parser.get_text()


def _normalize_rich_text(value: Any) -> str:
    if isinstance(value, str):
        return _html_to_text(value)
    if isinstance(value, dict):
        for key in ("body", "text", "name", "label", "value"):
            nested = value.get(key)
            if isinstance(nested, str):
                return _html_to_text(nested)
    return ""


def _categorize_feature(name: str, description: str) -> str:
    searchable = f"{name} {description}".lower()
    category_rules = (
        (
            "Performance",
            (
                "performance",
                "latency",
                "timeout",
                "throughput",
                "slow",
                "optimize",
                "scalab",
                "rate limit",
                "bottleneck",
                "response time",
                "high volume",
                "memory",
                "cpu",
                "concurren",
            ),
        ),
        (
            "Data Pipeline",
            (
                "kafka",
                "ingestion",
                "consumer",
                "producer",
                "pipeline",
                "bulkimport",
                "bulk import",
                "message queue",
                "event stream",
                "topic",
                "partition",
                "offset",
            ),
        ),
        (
            "Storage & Database",
            (
                "cosmos",
                "cockroachdb",
                "crdb",
                "azure sql",
                "sql table",
                "database",
                "migration",
                "schema",
                "cosmos db",
                "partition key",
                "document store",
                "blob storage",
            ),
        ),
        (
            "Consent API",
            (
                "api inconsistency",
                "api response",
                "api endpoint",
                "response payload",
                "request payload",
                "custom preference api",
                "/api/consent",
                "rest api",
                "/v1/",
                "/v2/",
                "/v3/",
                "/v4/",
                "consent ui",
                "receipt api",
                "api return",
                "filter",
                "api structure",
                "public api",
            ),
        ),
        (
            "Reporting & Audit",
            (
                "reporting",
                "audit trail",
                "audit log",
                "analytics",
                "history",
                "compliance report",
                "dashboard",
                "visibility",
                "tracking of",
                "historical",
                "record keeping",
            ),
        ),
        (
            "Identity & DSR",
            (
                "data subject right",
                "dsr",
                "linked identity",
                "identity group",
                "subject access",
                "erasure",
                "portability",
                "right to",
                "lig",
                "parent-child",
                "data subject group",
                "identifier type",
            ),
        ),
        (
            "Preference Center",
            (
                "preference center",
                "preference manager",
                "custom preference",
                "opt-in",
                "opt-out",
                "do not sell",
                "topic",
                "purpose",
                "preference ui",
                "web form",
                "collection point",
            ),
        ),
        (
            "Cookie & Consent String",
            (
                "cookie",
                "tracking",
                "pixel",
                "tag manager",
                "tcf",
                "gpp",
                "consent string",
                "banner",
                "cmp",
                "iab",
                "vendor list",
            ),
        ),
        (
            "Privacy Notices",
            (
                "privacy notice",
                "disclosure",
                "transparency",
                "notice version",
                "notice template",
                "dynamic notice",
            ),
        ),
        (
            "Integration & SDK",
            (
                "sdk",
                "mobile sdk",
                "android",
                "ios",
                "integration",
                "webhook",
                "third-party",
                "connector",
                "plugin",
                "mobile app",
                "cross-device",
                "cross device",
            ),
        ),
    )

    for category, keywords in category_rules:
        if any(keyword in searchable for keyword in keywords):
            return category

    for category, keywords in _load_dynamic_categories().items():
        if any(kw in searchable for kw in keywords):
            return category

    return "General"


def _is_recent_date(value: Any) -> bool:
    if not value:
        return True

    try:
        normalized = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized).date()
    except (TypeError, ValueError):
        return True

    cutoff = date.today() - timedelta(days=MAX_RECORD_AGE_DAYS)
    return parsed >= cutoff


class AhaService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.azure_openai_service = AzureOpenAIService()

    async def _suggest_and_register_category(self, name: str, description: str) -> str:
        if not self.azure_openai_service.is_configured():
            return "General"

        dynamic = _load_dynamic_categories()
        all_categories = STATIC_CATEGORIES + list(dynamic.keys())

        prompt = (
            "You are tagging product ideas for an internal consent management engineering tool.\n"
            f"Existing categories: {', '.join(all_categories)}.\n"
            "If the idea clearly belongs to one of the existing categories, return that exact name.\n"
            "Otherwise suggest a NEW concise 2-4 word developer-focused category.\n"
            "Reply with ONLY the category name. No explanation, no punctuation.\n\n"
            f"Idea: {name}\n"
            f"Description: {description[:600]}"
        )

        try:
            suggested = await self.azure_openai_service.create_response(
                [{"role": "user", "content": prompt}]
            )
            suggested = suggested.strip().strip("\"' ").strip()[:60]
        except Exception as exc:
            logger.warning("AI category suggestion failed: %s", exc)
            return "General"

        if not suggested:
            return "General"

        if suggested not in all_categories and suggested != "General":
            dynamic[suggested] = _extract_seed_keywords(name, description)
            _save_dynamic_categories(dynamic)
            logger.info(
                "Dynamic category registered: %s (seeds: %s)",
                suggested,
                dynamic[suggested],
            )

        return suggested

    async def fetch_ideas(self, limit: int = 200) -> list[dict[str, Any]]:
        if not self.settings.aha_api_key or not self.settings.aha_base_url:
            logger.warning("Aha credentials are not configured")
            return []

        product_key = self.settings.aha_product_key or "CD"
        endpoint = (
            f"{self.settings.aha_base_url}/products/{product_key}/ideas?sort=recent"
        )
        headers = {
            "Authorization": f"Bearer {self.settings.aha_api_key}",
            "Accept": "application/json",
        }
        params = {
            "per_page": limit,
            "fields": "id,reference_num,name,description,workflow_status,votes_count,url,created_at,score",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(endpoint, headers=headers, params=params)
            response.raise_for_status()
            payload = response.json()

        features: list[dict[str, Any]] = []
        for item in payload.get("ideas", []):
            if not _is_recent_date(item.get("created_at")):
                continue

            workflow = item.get("workflow_status") or {}
            name = _normalize_rich_text(item.get("name", ""))
            description = _normalize_rich_text(item.get("description", ""))
            category = _categorize_feature(name, description)
            if category == "General":
                category = await self._suggest_and_register_category(name, description)
            features.append(
                {
                    "id": str(item.get("id", "")),
                    "reference_num": item.get("reference_num", ""),
                    "name": name,
                    "description": description,
                    "status": workflow.get("name", "Not started"),
                    "priority": item.get("score")
                    or item.get("votes_count")
                    or "Medium",
                    "category": category,
                    "source_type": "aha_idea",
                    "due_date": item.get("created_at"),
                    "url": item.get("url", ""),
                }
            )

        return features
