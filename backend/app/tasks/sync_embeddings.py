"""Background task for generating embeddings."""

import logging
from app.tasks.scheduler import scheduler_service
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


async def generate_embeddings_task():
    """Background task to generate embeddings for all Confluence pages."""
    try:
        logger.info("Starting background embeddings generation")
        embedding_service = EmbeddingService()
        await embedding_service.index_all_pages()
        logger.info("Background embeddings generation completed")
    except Exception as e:
        logger.error(f"Background embeddings generation failed: {e}")


def schedule_embedding_generation():
    """Schedule periodic embedding generation."""
    if scheduler_service.scheduler:
        scheduler_service.scheduler.add_job(
            generate_embeddings_task,
            "interval",
            hours=6,  # Run every 6 hours
            id="embeddings_generation",
            name="Generate embeddings for Confluence pages",
            replace_existing=True,
        )
        logger.info("Scheduled embeddings generation to run every 6 hours")
