from __future__ import annotations

from openai import AsyncAzureOpenAI

from app.config import get_settings


class AzureOpenAIService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def is_configured(self) -> bool:
        return bool(
            self.settings.azure_openai_api_key
            and self.settings.azure_openai_endpoint
            and self.settings.azure_openai_chat_deployment
        )

    def embeddings_configured(self) -> bool:
        return bool(
            self.settings.azure_openai_api_key
            and self.settings.azure_openai_endpoint
            and self.settings.azure_openai_embedding_deployment
        )

    def get_chat_client(self) -> AsyncAzureOpenAI:
        return AsyncAzureOpenAI(
            api_key=self.settings.azure_openai_api_key,
            api_version=self.settings.azure_openai_api_version,
            azure_endpoint=self.settings.azure_openai_endpoint,
        )

    def get_embedding_client(self) -> AsyncAzureOpenAI:
        # Use standard OpenAI endpoint for embeddings, not Responses API
        endpoint = self.settings.azure_openai_endpoint.replace(
            "/openai/responses", "/openai"
        )
        return AsyncAzureOpenAI(
            api_key=self.settings.azure_openai_api_key,
            api_version=self.settings.azure_openai_embedding_api_version,
            azure_endpoint=endpoint,
        )

    async def create_embeddings(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        client = self.get_embedding_client()
        response = await client.embeddings.create(
            model=self.settings.azure_openai_embedding_deployment,
            input=texts,
        )
        return [item.embedding for item in response.data]

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        embeddings = await self.create_embeddings([text])
        return embeddings[0] if embeddings else []

    async def create_response(self, messages: list[dict]) -> str:
        """Create a response using the Responses API."""
        if not self.is_configured():
            return ""

        client = self.get_chat_client()

        # Convert messages to Responses API format
        input_messages = []
        for msg in messages:
            input_messages.append(
                {
                    "role": msg["role"],
                    "content": [{"type": "input_text", "text": msg["content"]}],
                }
            )

        response = await client.responses.create(
            model=self.settings.azure_openai_chat_deployment,
            input=input_messages,
        )

        # Extract text from response
        if response.output and len(response.output) > 0:
            output = response.output[0]
            if (
                hasattr(output, "content")
                and output.content
                and len(output.content) > 0
            ):
                content = output.content[0]
                if hasattr(content, "text"):
                    return content.text

        return ""
