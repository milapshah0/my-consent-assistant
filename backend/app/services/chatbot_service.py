from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from app.services.azure_openai_service import AzureOpenAIService
from app.services.confluence_service import ConfluenceService
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)
TERM_ALIASES: dict[str, set[str]] = {
    "crdb": {"crdb", "cockroachdb", "cockroach", "cockroach_db"},
    "cockroachdb": {"cockroachdb", "cockroach", "crdb", "cockroach_db"},
}


class ChatbotService:
    def __init__(self) -> None:
        self.confluence_service = ConfluenceService()
        self.azure_openai_service = AzureOpenAIService()
        self.embedding_service = EmbeddingService()

    async def ask(
        self,
        message: str,
        context_title: str | None = None,
        context_hint: str | None = None,
    ) -> dict:
        # Get recent pages from last 30 days for better results
        from datetime import datetime, timedelta, timezone

        recent_cutoff = (datetime.now(timezone.utc) - timedelta(days=365)).strftime(
            "%Y-%m-%d %H:%M"
        )

        pages = await self.confluence_service.fetch_pages(
            limit=100, since=recent_cutoff
        )

        # Prioritize recent/updated pages by sorting
        pages = self._sort_pages_by_recency(pages)

        matched_pages = self._match_items(pages, message, key="title")[:3]

        # If no matches found with recent pages, try with all pages
        if not matched_pages:
            all_pages = await self.confluence_service.fetch_pages(
                limit=200
            )  # Get all pages
            all_pages = self._sort_pages_by_recency(all_pages)
            matched_pages = self._match_items(all_pages, message, key="title")[:3]

        # If still no matches, try vector search with embeddings
        if not matched_pages:
            vector_pages = await self.embedding_service.search_similar_pages(
                message, limit=3
            )
            if vector_pages:
                matched_pages = vector_pages

        if not matched_pages:
            return {
                "answer": self._build_no_match_response(
                    message, context_title=context_title, context_hint=context_hint
                ),
                "sources": [],
                "message": message,
            }

        # Build a direct answer from the matched content if Azure OpenAI is not available
        if not self.azure_openai_service.is_configured():
            answer = self._build_direct_answer([], matched_pages, message)
            follow_up_questions = self._generate_follow_up_questions(
                [], matched_pages, message
            )
            return {
                "answer": answer + "\n\n" + follow_up_questions,
                "sources": self._build_sources([], matched_pages),
                "message": message,
            }

        sources = [
            *[
                {
                    "type": "confluence_page",
                    "title": page.get("title"),
                    "url": page.get("url"),
                }
                for page in matched_pages
            ],
        ]

        answer = await self._generate_answer(
            message,
            matched_pages,
            context_title=context_title,
            context_hint=context_hint,
        )

        return {
            "answer": answer,
            "sources": sources,
            "message": message,
        }

    async def _generate_answer(
        self,
        message: str,
        matched_pages: list[dict],
        context_title: str | None = None,
        context_hint: str | None = None,
    ) -> str:
        context_block = self._build_context_block(context_title, context_hint)
        fallback_answer = "\n\n".join(
            [
                "Here is a developer-focused answer based on current consent context:",
                context_block,
                self._build_focus_statement(matched_pages),
                self._build_guidance_statement(message),
            ]
        )
        if not self.azure_openai_service.is_configured():
            return fallback_answer

        page_context = "\n\n".join(
            [
                f"## {page.get('title')}\n{page.get('content', '')[:2000]}"
                for page in matched_pages
            ]
        )
        prompt = (
            "You are a technical consent engineering assistant. "
            "Use the provided Confluence documentation to answer with an implementation-focused, concise response. "
            "Prefer technical documentation evidence over product-style phrasing.\n\n"
            f"Workspace context: {context_block}\n\n"
            f"User question: {message}\n\n"
            f"Relevant Confluence pages:\n{page_context or '- None'}\n\n"
            "Answer with: 1) short summary, 2) technical considerations, 3) next implementation step."
        )

        try:
            response = await self.azure_openai_service.create_response(
                messages=[
                    {
                        "role": "system",
                        "content": "You answer as a senior engineer working on consent platform implementation.",
                    },
                    {"role": "user", "content": prompt},
                ]
            )
            if isinstance(response, str) and response.strip():
                return response.strip()
        except Exception:
            logger.exception("Azure OpenAI chat request failed")

        return fallback_answer

    @staticmethod
    def _sort_pages_by_recency(pages: list[dict]) -> list[dict]:
        """Sort pages by updated_at to prioritize recent content."""

        def get_updated_at(page: dict) -> datetime:
            updated = page.get("updated_at")
            if isinstance(updated, str):
                try:
                    return datetime.fromisoformat(updated.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass
            return datetime.min.replace(tzinfo=timezone.utc)

        return sorted(pages, key=get_updated_at, reverse=True)

    @staticmethod
    def _build_direct_answer(self, matched_pages: list[dict], message: str) -> str:
        """Build a direct answer from matched content without AI."""
        if not matched_pages:
            return self._build_no_match_response(message)

        answer_parts = []

        if matched_pages:
            answer_parts.append("Based on the available Confluence documentation:")

            for page in matched_pages:
                title = page.get("title", "Untitled")
                content = page.get("content", "")
                excerpt = page.get("excerpt", "")

                # Use content or excerpt, clean HTML tags properly
                text_content = content if content else excerpt
                if text_content:
                    # Better HTML cleaning
                    clean_text = self._clean_html_content(text_content)

                    # Take first 400 characters for readability
                    summary = (
                        clean_text[:400] + "..."
                        if len(clean_text) > 400
                        else clean_text
                    )
                    answer_parts.append(f"\n**{title}**\n{summary}")

        return "\n".join(answer_parts)

    def _clean_html_content(self, html_content: str) -> str:
        """Clean HTML content and extract readable text."""
        if not html_content:
            return ""

        import re

        # Remove ALL Confluence macros and structured content
        html_content = re.sub(
            r"<ac:structured-macro[^>]*>.*?</ac:structured-macro>",
            "",
            html_content,
            flags=re.DOTALL,
        )
        html_content = re.sub(
            r"<ac:rich-text-body[^>]*>.*?</ac:rich-text-body>",
            "",
            html_content,
            flags=re.DOTALL,
        )
        html_content = re.sub(
            r"<ac:plain-text-body[^>]*>.*?</ac:plain-text-body>",
            "",
            html_content,
            flags=re.DOTALL,
        )
        html_content = re.sub(
            r"<ri:page[^>]*>.*?</ri:page>", "", html_content, flags=re.DOTALL
        )
        html_content = re.sub(
            r"<ri:user[^>]*>.*?</ri:user>", "", html_content, flags=re.DOTALL
        )
        html_content = re.sub(
            r"<ri:attachment[^>]*>.*?</ri:attachment>",
            "",
            html_content,
            flags=re.DOTALL,
        )
        html_content = re.sub(
            r"<ri:url[^>]*>.*?</ri:url>", "", html_content, flags=re.DOTALL
        )

        # Remove table of contents and navigation
        html_content = re.sub(
            r"<h\d>.*?Table of Contents.*?</h\d>",
            "",
            html_content,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # Remove status macros and badges
        html_content = re.sub(
            r"Status\s+(Complete|In Progress|Not Started)\s*(Green|Red|Yellow|Blue)",
            "",
            html_content,
            flags=re.IGNORECASE,
        )
        html_content = re.sub(
            r"Impact\s+(High|Medium|Low)\s*(Green|Red|Yellow|Blue)",
            "",
            html_content,
            flags=re.IGNORECASE,
        )

        # Remove @mentions and metadata
        html_content = re.sub(r"@[^\s]+", "", html_content)
        html_content = re.sub(r"Driver\s+@.*", "", html_content)
        html_content = re.sub(r"Approver\s+@.*", "", html_content)
        html_content = re.sub(r"Contributors\s+@.*", "", html_content)
        html_content = re.sub(r"Informed\s+@.*", "", html_content)

        # Remove HTML tags
        html_content = re.sub(r"<[^>]+>", " ", html_content)

        # Handle common HTML entities
        html_content = html_content.replace("&nbsp;", " ")
        html_content = html_content.replace("&amp;", "&")
        html_content = html_content.replace("&lt;", "<")
        html_content = html_content.replace("&gt;", ">")
        html_content = html_content.replace("&quot;", '"')
        html_content = html_content.replace("&#39;", "'")
        html_content = html_content.replace("&mdash;", "—")
        html_content = html_content.replace("&ndash;", "–")

        # Clean up whitespace and line breaks
        html_content = re.sub(r"\s+", " ", html_content)
        html_content = html_content.strip()

        # Remove Confluence-specific patterns
        html_content = re.sub(
            r"Type\s*//.*", "", html_content
        )  # Remove Type // comments
        html_content = re.sub(
            r"Resources\s*Type.*", "", html_content
        )  # Remove Resources sections

        return html_content

    def _generate_follow_up_questions(
        self, matched_pages: list[dict], message: str
    ) -> str:
        """Generate relevant follow-up questions based on matched content."""
        questions = []

        # Extract key topics from matched pages
        page_titles = [page.get("title", "").lower() for page in matched_pages]

        # Generate contextual follow-up questions
        if any("blob" in title for title in page_titles):
            questions.extend(
                [
                    "What are the key differences between Blob V1 and V2?",
                    "How does the migration from V1 to V2 impact performance?",
                    "What are the storage implications of Blob V2?",
                ]
            )

        if any("cockroach" in title for title in page_titles):
            questions.extend(
                [
                    "What are the performance benchmarks for CockroachDB?",
                    "How does CockroachDB handle scaling?",
                    "What are the deployment considerations for CockroachDB?",
                ]
            )

        if any("consent" in title for title in page_titles):
            questions.extend(
                [
                    "What are the latest consent management patterns?",
                    "How does consent data flow through the system?",
                    "What are the compliance requirements for consent?",
                ]
            )

        if any("database" in title for title in page_titles):
            questions.extend(
                [
                    "What are the database scaling strategies?",
                    "How does database performance impact consent processing?",
                    "What are the database backup and recovery procedures?",
                ]
            )

        # Generic follow-up questions if no specific topics found
        if not questions:
            questions.extend(
                [
                    "What are the implementation details for this topic?",
                    "How does this relate to consent management?",
                    "What are the next steps for this initiative?",
                ]
            )

        # Return top 3 questions
        return "\n\n**Follow-up questions:**\n" + "\n".join(
            f"• {q}" for q in questions[:3]
        )

    def _build_sources(self, pages: list[dict]) -> list[dict]:
        """Build sources list."""
        sources = []

        # Add Confluence pages
        for page in pages:
            sources.append(
                {
                    "type": "confluence_page",
                    "title": page.get("title"),
                    "url": page.get("url"),
                }
            )

        return sources

    @staticmethod
    def _match_items(
        items: list[dict], query: str, key: str, threshold: int | None = None
    ) -> list[dict]:
        query_tokens = ChatbotService._extract_query_tokens(query)
        if not query_tokens:
            return []

        scored: list[tuple[int, dict]] = []
        for item in items:
            searchable_parts = [
                str(item.get(key, "")),
                str(item.get("description", "")),
                str(item.get("excerpt", "")),
                str(item.get("category", "")),
            ]
            text = " ".join(searchable_parts).lower()
            normalized_text = ChatbotService._normalize_for_matching(text)
            expanded_query_tokens = ChatbotService._expand_query_tokens(query_tokens)
            score = sum(
                1
                for token in expanded_query_tokens
                if token in text
                or ChatbotService._normalize_for_matching(token) in normalized_text
            )
            score_threshold = (
                threshold if threshold is not None else min(2, len(query_tokens))
            )
            if score >= score_threshold:
                scored.append((score, item))

        scored.sort(key=lambda row: row[0], reverse=True)
        return [item for _, item in scored]

    @staticmethod
    def _extract_query_tokens(query: str) -> set[str]:
        stop_words = {
            "the",
            "and",
            "for",
            "with",
            "from",
            "that",
            "this",
            "give",
            "details",
            "about",
            "using",
            "current",
            "workspace",
            "context",
            "active",
            "filters",
            "visible",
            "items",
            "source",
            "inbox",
        }
        return {
            token
            for token in re.findall(r"[a-zA-Z0-9_-]+", query.lower())
            if len(token) > 2 and token not in stop_words
        }

    @staticmethod
    def _expand_query_tokens(tokens: set[str]) -> set[str]:
        expanded = set(tokens)
        for token in tokens:
            expanded.update(TERM_ALIASES.get(token, set()))
        return expanded

    @staticmethod
    def _normalize_for_matching(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", value.lower())

    @staticmethod
    def _build_context_block(
        context_title: str | None,
        context_hint: str | None,
    ) -> str:
        if not context_title and not context_hint:
            return "No additional workspace context provided."
        if context_title and context_hint:
            return f"{context_title} — {context_hint}"
        return (
            context_title or context_hint or "No additional workspace context provided."
        )

    @staticmethod
    def _build_no_match_response(
        message: str,
        context_title: str | None = None,
        context_hint: str | None = None,
    ) -> str:
        context_block = ChatbotService._build_context_block(context_title, context_hint)
        return "\n\n".join(
            [
                "I could not find relevant indexed Confluence documents for this question.",
                f"Workspace context: {context_block}",
                f"Question: {message}",
                "Suggested next step: ask about a synced consent topic, or index documentation related to this technology before using the assistant for grounded answers.",
            ]
        )

    @staticmethod
    def _build_focus_statement(pages: list[dict]) -> str:
        if not pages:
            return "No direct page match found yet. Start by selecting one target page and then ask for related implementation patterns."

        page_titles = ", ".join([p.get("title", "") for p in pages if p.get("title")])

        return f"Related documentation pages: {page_titles or 'N/A'}."

    @staticmethod
    def _build_guidance_statement(message: str) -> str:
        return (
            "Suggested next step: convert this into a clear problem statement, then define acceptance criteria and technical approach. "
            f"Current question captured: '{message}'."
        )
