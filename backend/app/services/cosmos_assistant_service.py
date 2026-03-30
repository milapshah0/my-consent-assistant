from __future__ import annotations

import json
import logging
import re

from app.schemas.cosmos import CosmosAssistantRequest, CosmosAssistantResponse
from app.services.azure_openai_service import AzureOpenAIService

logger = logging.getLogger(__name__)

QUERY_BLOCK_PATTERN = re.compile(r"```(?:sql)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
SQL_LINE_PATTERN = re.compile(r"(?im)^\s*select\b.*?(?:;\s*)?$", re.DOTALL)


class CosmosAssistantService:
    def __init__(self) -> None:
        self.azure_openai_service = AzureOpenAIService()

    async def assist(self, payload: CosmosAssistantRequest) -> CosmosAssistantResponse:
        fallback_answer = self._build_fallback_answer(payload)
        if not self.azure_openai_service.is_configured():
            return CosmosAssistantResponse(
                answer=fallback_answer,
                suggested_query=self._build_fallback_query(payload),
                follow_up_questions=self._build_follow_up_questions(payload),
            )

        prompt = self._build_prompt(payload)
        try:
            response = await self.azure_openai_service.create_response(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a Cosmos DB diagnostics assistant. "
                            "Help the user prepare queries, explain diagnostics results, and recreate better queries. "
                            "Be precise, technical, and concrete. When proposing a query, include exactly one Cosmos SQL query in a fenced sql block."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            if isinstance(response, str) and response.strip():
                return CosmosAssistantResponse(
                    answer=response.strip(),
                    suggested_query=self._extract_suggested_query(response),
                    follow_up_questions=self._build_follow_up_questions(payload),
                )
        except Exception:
            logger.exception("Cosmos AI assistant request failed")

        return CosmosAssistantResponse(
            answer=fallback_answer,
            suggested_query=self._build_fallback_query(payload),
            follow_up_questions=self._build_follow_up_questions(payload),
        )

    def _build_prompt(self, payload: CosmosAssistantRequest) -> str:
        diagnostics_summary = json.dumps(payload.diagnostics_result or {}, indent=2)[
            :12000
        ]
        return (
            f"Action: {payload.action}\n"
            f"Container: {payload.container_name}\n"
            f"Logical type: {payload.logical_type or 'Not provided'}\n"
            f"Partition key field: {payload.partition_key_field or 'Unknown'}\n"
            f"Partition key value: {payload.partition_key_value or 'Not provided'}\n"
            f"Current query: {payload.current_query or 'None'}\n\n"
            f"User request: {payload.prompt}\n\n"
            "Current diagnostics result:\n"
            f"{diagnostics_summary or '{}'}\n\n"
            "Respond with: 1) short answer, 2) reasoning, 3) recommended next query if useful."
        )

    def _build_fallback_answer(self, payload: CosmosAssistantRequest) -> str:
        query = self._build_fallback_query(payload)
        return "\n\n".join(
            [
                f"Action: {payload.action}",
                f"Container: {payload.container_name}",
                f"Logical type: {payload.logical_type or 'Not provided'}",
                "Use the current diagnostics result to compare RU, partition scope, and type filtering.",
                f"Suggested next query:\n```sql\n{query}\n```",
            ]
        )

    def _build_fallback_query(self, payload: CosmosAssistantRequest) -> str:
        base_query = payload.current_query or "SELECT TOP 10 * FROM c"
        if (
            payload.logical_type
            and "@logicalType" not in base_query
            and "type" not in base_query.lower()
        ):
            if " where " in base_query.lower():
                return f"{base_query} AND c.type = @logicalType"
            return f"{base_query} WHERE c.type = @logicalType"
        return base_query

    def _build_follow_up_questions(self, payload: CosmosAssistantRequest) -> list[str]:
        return [
            f"Can you compare RU for the same query on {payload.container_name} with and without the type filter?",
            "Can you rewrite the query to project only the fields I need instead of SELECT *?",
            "Can you explain whether the current result suggests a cross-partition scan?",
        ]

    def _extract_suggested_query(self, content: str) -> str | None:
        fenced_match = QUERY_BLOCK_PATTERN.search(content)
        if fenced_match:
            candidate = fenced_match.group(1).strip()
            return candidate or None
        select_match = SQL_LINE_PATTERN.search(content)
        if select_match:
            candidate = select_match.group(0).strip()
            return candidate or None
        return None
