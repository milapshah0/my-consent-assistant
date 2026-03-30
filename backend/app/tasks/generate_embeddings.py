import logging

from sqlalchemy import select

from app.database import SessionLocal
from app.models.aha_feature import AhaFeature
from app.models.confluence_page import ConfluencePage
from app.models.embedding import Embedding
from app.services.azure_openai_service import AzureOpenAIService

logger = logging.getLogger(__name__)


async def generate_embeddings() -> None:
    logger.info("generate_embeddings started")
    service = AzureOpenAIService()
    if not service.embeddings_configured():
        logger.info(
            "generate_embeddings skipped because Azure embedding settings are not configured"
        )
        return

    logger.info(
        "generate_embeddings ready with deployment=%s",
        service.settings.azure_openai_embedding_deployment,
    )

    # Generate embeddings for Confluence pages
    await _generate_confluence_embeddings(service)

    # Generate embeddings for Aha features
    await _generate_aha_embeddings(service)

    logger.info("generate_embeddings finished")


async def _generate_confluence_embeddings(service: AzureOpenAIService) -> None:
    """Generate embeddings for Confluence pages."""
    logger.info("Generating embeddings for Confluence pages")

    with SessionLocal() as db:
        # Get pages without embeddings
        pages_query = (
            select(ConfluencePage)
            .outerjoin(
                Embedding,
                (Embedding.content_type == "confluence_page")
                & (Embedding.content_id == ConfluencePage.id),
            )
            .where(Embedding.id.is_(None))
        )

        pages = db.execute(pages_query).scalars().all()
        logger.info(f"Found {len(pages)} Confluence pages without embeddings")

        for page in pages:
            try:
                # Combine title and content for embedding
                text = f"{page.title}\n{page.excerpt}\n{page.content}"

                # Generate embedding
                embedding = await service.generate_embedding(text)

                # Store embedding
                db.add(
                    Embedding(
                        content_type="confluence_page",
                        content_id=page.id,
                        embedding_model=service.settings.azure_openai_embedding_deployment,
                        embedding=embedding,
                        text_chunk=text[:2000],  # Truncate if needed
                    )
                )

                logger.debug(f"Generated embedding for page: {page.title}")

            except Exception as e:
                logger.error(f"Failed to generate embedding for page {page.id}: {e}")

        db.commit()


async def _generate_aha_embeddings(service: AzureOpenAIService) -> None:
    """Generate embeddings for Aha features."""
    logger.info("Generating embeddings for Aha features")

    with SessionLocal() as db:
        # Get features without embeddings
        features_query = (
            select(AhaFeature)
            .outerjoin(
                Embedding,
                (Embedding.content_type == "aha_feature")
                & (Embedding.content_id == AhaFeature.id),
            )
            .where(Embedding.id.is_(None))
        )

        features = db.execute(features_query).scalars().all()
        logger.info(f"Found {len(features)} Aha features without embeddings")

        for feature in features:
            try:
                # Combine name and description for embedding
                text = f"{feature.name}\n{feature.description}"

                # Generate embedding
                embedding = await service.generate_embedding(text)

                # Store embedding
                db.add(
                    Embedding(
                        content_type="aha_feature",
                        content_id=feature.id,
                        embedding_model=service.settings.azure_openai_embedding_deployment,
                        embedding=embedding,
                        text_chunk=text[:2000],  # Truncate if needed
                    )
                )

                logger.debug(f"Generated embedding for feature: {feature.name}")

            except Exception as e:
                logger.error(
                    f"Failed to generate embedding for feature {feature.id}: {e}"
                )

        db.commit()
