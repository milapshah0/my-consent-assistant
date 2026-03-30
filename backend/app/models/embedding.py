from __future__ import annotations

from pgvector.sqlalchemy import Vector
from sqlalchemy import Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    content_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'confluence_page' or 'aha_feature'
    content_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )  # FK to confluence_pages.id or aha_features.id
    embedding_model: Mapped[str] = mapped_column(
        String(100), default="text-embedding-3-small"
    )
    embedding: Mapped[Vector] = mapped_column(
        Vector(1536)
    )  # Adjust dimension based on model
    text_chunk: Mapped[str] = mapped_column(String(2000))  # The text that was embedded
    chunk_index: Mapped[int] = mapped_column(
        Integer, default=0
    )  # For large documents split into chunks
    extra_data: Mapped[dict] = mapped_column(JSON)  # Additional metadata

    __table_args__ = (
        Index("idx_content_type_id", "content_type", "content_id"),
        Index(
            "idx_embedding_vector",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
        ),
    )
