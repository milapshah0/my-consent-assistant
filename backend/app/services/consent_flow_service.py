from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path

from app.services.azure_openai_service import AzureOpenAIService

logger = logging.getLogger(__name__)

DOCS_DIR = Path(__file__).parent.parent.parent.parent / "docs"
CONSENT_FLOW_MD = DOCS_DIR / "consent_flow.md"
EMBEDDINGS_CACHE = DOCS_DIR / "consent_flow_embeddings.json"


class ConsentFlowService:
    def __init__(self) -> None:
        self.azure_openai_service = AzureOpenAIService()
        self._sections: list[dict] | None = None
        self._embeddings_cache: dict | None = None

    def _make_id(self, title: str) -> str:
        text = title.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"[\s_]+", "-", text.strip())
        text = re.sub(r"-+", "-", text).strip("-")
        return text

    def _detect_service(self, title: str, content: str) -> str:
        combined = (title + " " + content).lower()
        if "ds-request" in combined or "dsrequest" in combined:
            return "ds-request"
        if "consent-transaction" in combined:
            return "consent-transaction"
        if "consentmanager" in combined:
            return "consentmanager"
        if "ds-preference-cache" in combined or "preference-cache" in combined:
            return "ds-preference-cache"
        if "consent-data-manager" in combined:
            return "consent-data-manager"
        if "cosmos" in combined:
            return "cosmos"
        if "kafka" in combined:
            return "kafka"
        return "general"

    def _detect_phase(self, title: str, content: str) -> str:
        combined = (title + " " + content).lower()
        if "receipt creation" in combined or "post /request" in combined:
            return "ingestion"
        if "ingestion" in combined or "ingest" in combined:
            return "ingestion"
        if "kafka consumer" in combined:
            return "processing"
        if "cosmos" in combined and ("write" in combined or "parallel" in combined):
            return "storage"
        if "preference-cache" in combined or "blob" in combined:
            return "caching"
        if "public api" in combined or "get /v" in combined or "post /v" in combined:
            return "query"
        if "linked identity" in combined or "data subject groups" in combined:
            return "identity"
        return "general"

    def _parse_sections(self) -> list[dict]:
        if not CONSENT_FLOW_MD.exists():
            logger.warning("consent_flow.md not found at %s", CONSENT_FLOW_MD)
            return []

        content = CONSENT_FLOW_MD.read_text(encoding="utf-8")
        sections: list[dict] = []
        parts = re.split(r"^(#{1,4} .+)$", content, flags=re.MULTILINE)

        current_title = ""
        current_content = ""
        current_level = 0

        for part in parts:
            heading_match = re.match(r"^(#{1,4}) (.+)$", part.strip())
            if heading_match:
                if current_title and current_content.strip():
                    sections.append(
                        {
                            "id": self._make_id(current_title),
                            "title": current_title,
                            "content": current_content.strip(),
                            "level": current_level,
                            "service": self._detect_service(
                                current_title, current_content
                            ),
                            "phase": self._detect_phase(current_title, current_content),
                        }
                    )
                current_level = len(heading_match.group(1))
                current_title = heading_match.group(2).strip()
                current_content = ""
            else:
                current_content += part

        if current_title and current_content.strip():
            sections.append(
                {
                    "id": self._make_id(current_title),
                    "title": current_title,
                    "content": current_content.strip(),
                    "level": current_level,
                    "service": self._detect_service(current_title, current_content),
                    "phase": self._detect_phase(current_title, current_content),
                }
            )

        return sections

    def get_sections(self) -> list[dict]:
        if self._sections is None:
            self._sections = self._parse_sections()
        return self._sections

    def _load_embeddings_cache(self) -> dict:
        if self._embeddings_cache is not None:
            return self._embeddings_cache
        if EMBEDDINGS_CACHE.exists():
            try:
                data = json.loads(EMBEDDINGS_CACHE.read_text(encoding="utf-8"))
                self._embeddings_cache = data
                return data
            except Exception as exc:
                logger.warning("Failed to load embeddings cache: %s", exc)
        return {}

    def _save_embeddings_cache(self, cache: dict) -> None:
        try:
            DOCS_DIR.mkdir(parents=True, exist_ok=True)
            EMBEDDINGS_CACHE.write_text(json.dumps(cache), encoding="utf-8")
            self._embeddings_cache = cache
        except Exception as exc:
            logger.warning("Failed to save embeddings cache: %s", exc)

    def _content_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        if len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = sum(a * a for a in vec1) ** 0.5
        mag2 = sum(b * b for b in vec2) ** 0.5
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)

    async def index_sections(self) -> dict:
        if not self.azure_openai_service.embeddings_configured():
            return {"indexed": 0, "total": 0, "message": "Embeddings not configured"}

        self._sections = None
        sections = self.get_sections()
        cache = self._load_embeddings_cache()
        indexed = 0

        for section in sections:
            section_id = section["id"]
            full_text = f"{section['title']}\n\n{section['content']}"
            content_hash = self._content_hash(full_text)

            if cache.get(section_id, {}).get("hash") == content_hash:
                continue

            try:
                embedding = await self.azure_openai_service.generate_embedding(
                    full_text[:6000]
                )
                cache[section_id] = {
                    "hash": content_hash,
                    "embedding": embedding,
                    "title": section["title"],
                }
                indexed += 1
            except Exception as exc:
                logger.error("Failed to embed section %s: %s", section_id, exc)

        self._save_embeddings_cache(cache)
        return {
            "indexed": indexed,
            "total": len(sections),
            "message": "Indexing complete",
        }

    async def _search_sections(self, query: str, limit: int = 5) -> list[dict]:
        sections = self.get_sections()
        cache = self._load_embeddings_cache()

        if not cache or not self.azure_openai_service.embeddings_configured():
            query_lower = query.lower()
            scored = [
                (
                    sum(
                        1
                        for word in query_lower.split()
                        if word in (s["title"] + " " + s["content"]).lower()
                    ),
                    s,
                )
                for s in sections
            ]
            scored.sort(key=lambda x: x[0], reverse=True)
            return [s for score, s in scored[:limit] if score > 0] or sections[:limit]

        try:
            query_embedding = await self.azure_openai_service.generate_embedding(query)
            scored = []
            for section in sections:
                entry = cache.get(section["id"])
                if entry and "embedding" in entry:
                    sim = self._cosine_similarity(query_embedding, entry["embedding"])
                    scored.append((sim, section))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [s for _, s in scored[:limit]]
        except Exception as exc:
            logger.error("Vector search failed: %s", exc)
            return sections[:limit]

    async def ask(self, question: str, section_id: str | None = None) -> dict:
        if section_id:
            sections = self.get_sections()
            relevant = [s for s in sections if s["id"] == section_id]
            if not relevant:
                relevant = await self._search_sections(question)
        else:
            relevant = await self._search_sections(question)

        if not relevant:
            return {
                "answer": "No relevant information found in the consent flow documentation.",
                "sections_used": [],
                "follow_up_questions": [],
            }

        context = "\n\n---\n\n".join(
            f"### {s['title']}\n{s['content'][:2500]}" for s in relevant
        )

        if not self.azure_openai_service.is_configured():
            answer = "\n\n".join(
                f"**{s['title']}**\n{s['content'][:400]}" for s in relevant
            )
            return {
                "answer": answer,
                "sections_used": [
                    {"id": s["id"], "title": s["title"]} for s in relevant
                ],
                "follow_up_questions": [],
            }

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert on OneTrust's consent management system architecture. "
                    "Answer questions based on the provided consent flow documentation. "
                    "Be concise and technical. Use bullet points where appropriate. "
                    "Reference specific services, Kafka topics, and API endpoints when relevant."
                ),
            },
            {
                "role": "user",
                "content": f"Context from consent flow documentation:\n\n{context}\n\n---\n\nQuestion: {question}",
            },
        ]

        try:
            answer = await self.azure_openai_service.create_response(messages)
        except Exception as exc:
            logger.error("AI response failed: %s", exc)
            answer = "\n\n".join(
                f"**{s['title']}**: {s['content'][:300]}" for s in relevant
            )

        return {
            "answer": answer,
            "sections_used": [{"id": s["id"], "title": s["title"]} for s in relevant],
            "follow_up_questions": [
                "What Kafka topics are involved in this flow?",
                "How does the Cosmos DB write path work?",
                "What are the escape lane scenarios?",
                "How are linked identity groups handled?",
            ],
        }
