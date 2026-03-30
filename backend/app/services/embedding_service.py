import hashlib
import json
import logging
from typing import List

from app.database import SessionLocal
from app.models.confluence_page import ConfluencePage
from app.models.confluence_page_embedding import ConfluencePageEmbedding
from app.services.azure_openai_service import AzureOpenAIService

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self) -> None:
        self.azure_openai_service = AzureOpenAIService()

    def _generate_content_hash(self, content: str) -> str:
        """Generate a hash of the content to detect changes."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _chunk_content(self, content: str, max_tokens: int = 2000) -> List[str]:
        """Split content into chunks that fit within token limits."""
        # Rough estimation: 1 token ≈ 4 characters, use conservative estimate
        max_chars = max_tokens * 3  # More conservative: 3 chars per token

        if len(content) <= max_chars:
            return [content]

        chunks = []
        current_chunk = ""

        # Split by paragraphs first
        paragraphs = content.split("\n\n")

        for paragraph in paragraphs:
            # If adding this paragraph exceeds limit, start new chunk
            if len(current_chunk) + len(paragraph) + 2 > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = paragraph
                else:
                    # Single paragraph too long, split by sentences
                    sentences = paragraph.split(". ")
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) + 2 > max_chars:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                                current_chunk = sentence
                            else:
                                # Single sentence too long, split by words
                                words = sentence.split(" ")
                                for word in words:
                                    if len(current_chunk) + len(word) + 1 > max_chars:
                                        if current_chunk:
                                            chunks.append(current_chunk.strip())
                                            current_chunk = word
                                        else:
                                            chunks.append(word)
                                    else:
                                        current_chunk += (
                                            " " + word if current_chunk else word
                                        )
                        else:
                            current_chunk += (
                                ". " + sentence if current_chunk else sentence
                            )
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    async def generate_embeddings_for_pages(self, pages: List[dict]) -> None:
        """Generate and store embeddings for a list of Confluence pages."""
        if not self.azure_openai_service.embeddings_configured():
            logger.info("Embeddings not configured - skipping vector indexing")
            return

        with SessionLocal() as db:
            for page in pages:
                try:
                    page_id = page.get("id")
                    content = page.get("content", "")
                    title = page.get("title", "")

                    # Combine title and content for better search results
                    full_content = f"{title}\n\n{content}"
                    content_hash = self._generate_content_hash(full_content)

                    # Check if embedding already exists and is up to date
                    existing = (
                        db.query(ConfluencePageEmbedding)
                        .filter(ConfluencePageEmbedding.page_id == page_id)
                        .first()
                    )

                    if existing and existing.content_hash == content_hash:
                        logger.debug(f"Embedding up to date for page: {title}")
                        continue

                    # Delete existing embeddings for this page
                    if existing:
                        db.query(ConfluencePageEmbedding).filter(
                            ConfluencePageEmbedding.page_id == page_id
                        ).delete()

                    # Chunk content to handle large pages
                    chunks = self._chunk_content(full_content)
                    logger.info(f"Processing {len(chunks)} chunks for page: {title}")

                    # Generate embedding for each chunk
                    for i, chunk in enumerate(chunks):
                        try:
                            # Additional safety check: if chunk is too large, truncate it
                            if len(chunk) > 8000:  # Very conservative character limit
                                chunk = chunk[:8000]
                                logger.warning(
                                    f"Truncated oversized chunk {i + 1} for page: {title}"
                                )

                            embedding_vector = (
                                await self.azure_openai_service.generate_embedding(
                                    chunk
                                )
                            )
                            embedding_json = json.dumps(embedding_vector)

                            # Create embedding record with chunk info
                            chunk_id = f"{page_id}_chunk_{i}"
                            embedding = ConfluencePageEmbedding(
                                id=chunk_id,
                                page_id=page_id,
                                embedding=embedding_json,
                                content_hash=content_hash,
                            )
                            db.add(embedding)
                            logger.debug(
                                f"Created embedding for chunk {i + 1}/{len(chunks)} of page: {title}"
                            )

                        except Exception as e:
                            logger.error(
                                f"Failed to generate embedding for chunk {i + 1} of page {title}: {e}"
                            )
                            continue

                except Exception as e:
                    logger.error(
                        f"Failed to generate embedding for page {page.get('title', 'unknown')}: {e}"
                    )
                    continue

            try:
                db.commit()
                logger.info(f"Successfully processed embeddings for {len(pages)} pages")
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to commit embeddings: {e}")

    async def search_similar_pages(self, query: str, limit: int = 5) -> List[dict]:
        """Search for pages similar to the query using vector similarity."""
        if not self.azure_openai_service.embeddings_configured():
            logger.info("Embeddings not configured - falling back to keyword search")
            return []

        try:
            # Generate embedding for the query
            query_embedding = await self.azure_openai_service.generate_embedding(query)

            with SessionLocal() as db:
                # Get all embeddings
                embeddings = db.query(ConfluencePageEmbedding).all()

                if not embeddings:
                    return []

                # Calculate similarity scores for all chunks
                chunk_scores = []
                for embedding_record in embeddings:
                    try:
                        stored_embedding = json.loads(embedding_record.embedding)
                        similarity = self._cosine_similarity(
                            query_embedding, stored_embedding
                        )

                        chunk_scores.append(
                            {
                                "page_id": embedding_record.page_id,
                                "chunk_id": embedding_record.id,
                                "similarity": similarity,
                            }
                        )
                    except Exception as e:
                        logger.error(
                            f"Error calculating similarity for chunk {embedding_record.id}: {e}"
                        )
                        continue

                # Group chunks by page_id and find the best similarity per page
                page_scores = {}
                for chunk in chunk_scores:
                    page_id = chunk["page_id"]
                    if (
                        page_id not in page_scores
                        or chunk["similarity"] > page_scores[page_id]["similarity"]
                    ):
                        page_scores[page_id] = chunk

                # Sort pages by best similarity score
                sorted_pages = sorted(
                    page_scores.values(), key=lambda x: x["similarity"], reverse=True
                )

                # Get page details for top results
                results = []
                for page_chunk in sorted_pages[:limit]:
                    # Get the associated page
                    from app.models.confluence_page import ConfluencePage

                    page = (
                        db.query(ConfluencePage)
                        .filter(ConfluencePage.id == page_chunk["page_id"])
                        .first()
                    )

                    if page:
                        results.append(
                            {
                                "id": page.id,
                                "title": page.title,
                                "content": page.content,
                                "url": page.url,
                                "similarity_score": page_chunk["similarity"],
                            }
                        )

                return results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    async def index_all_pages(self) -> None:
        """Generate embeddings for all Confluence pages in the database."""
        logger.info("Starting vector indexing for all Confluence pages")

        with SessionLocal() as db:
            pages = db.query(ConfluencePage).all()

        if not pages:
            logger.info("No Confluence pages found for indexing")
            return

        # Convert to dict format for processing
        page_dicts = [
            {
                "id": page.id,
                "title": page.title,
                "content": page.content,
                "url": page.url,
            }
            for page in pages
        ]

        await self.generate_embeddings_for_pages(page_dicts)
        logger.info(f"Completed vector indexing for {len(page_dicts)} pages")
