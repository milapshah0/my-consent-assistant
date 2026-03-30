import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.services.embedding_service import EmbeddingService
from app.tasks.scheduler import scheduler_service
from app.tasks.sync_aha import sync_aha_features
from app.tasks.sync_confluence import sync_confluence_pages
from app.tasks.sync_embeddings import schedule_embedding_generation

settings = get_settings()
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Application startup initiated")
    logger.info("Startup step 1/5: syncing Confluence pages")
    await sync_confluence_pages(force=False)
    await sync_aha_features()
    logger.info("Startup step 1/5 complete: Confluence sync finished")

    logger.info("Startup step 2/5: generating embeddings")
    try:
        embedding_service = EmbeddingService()
        await embedding_service.index_all_pages()
        logger.info("Startup step 2/5 complete: embeddings generated")
    except Exception as e:
        logger.error(f"Startup step 2/5 failed: {e}")

    if settings.background_jobs_enabled:
        logger.info("Startup step 3/5: starting background scheduler")
        scheduler_service.start()
        schedule_embedding_generation()
        logger.info("Startup step 4/5 complete: background scheduler started")
    else:
        logger.info("Startup step 4/5 skipped: background jobs disabled")

    logger.info("Startup step 5/5 complete: application ready")
    yield

    logger.info("Application shutdown initiated")
    if settings.background_jobs_enabled:
        scheduler_service.stop()
        logger.info("Background scheduler stopped")
    logger.info("Application shutdown complete")


app = FastAPI(
    title="Consent Dashboard API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Consent Dashboard API is running"}
