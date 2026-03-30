"""Embedding management endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/embeddings", tags=["embeddings"])


@router.post("/index-all")
async def index_all_pages(db: Session = Depends(get_db_session)):
    """Generate embeddings for all Confluence pages."""
    try:
        embedding_service = EmbeddingService()
        await embedding_service.index_all_pages()
        return {"message": "Embedding indexing completed"}
    except Exception as e:
        logger.error(f"Embedding indexing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/{page_id}")
async def generate_page_embedding(page_id: str, db: Session = Depends(get_db_session)):
    """Generate embedding for a specific Confluence page."""
    try:
        from app.models.confluence_page import ConfluencePage

        page = db.query(ConfluencePage).filter(ConfluencePage.id == page_id).first()
        if not page:
            raise HTTPException(status_code=404, detail="Page not found")

        embedding_service = EmbeddingService()
        page_dict = {
            "id": page.id,
            "title": page.title,
            "content": page.content,
            "url": page.url,
        }

        await embedding_service.generate_embeddings_for_pages([page_dict])
        return {"message": f"Embedding generated for page {page_id}"}
    except Exception as e:
        logger.error(f"Page embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
