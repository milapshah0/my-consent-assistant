"""Add confluence page embeddings table

Revision ID: 20260326_0004
Revises: 20260326_0003
Create Date: 2026-03-26 16:37:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260326_0004'
down_revision: Union[str, None] = '20260326_0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create confluence_page_embeddings table
    op.create_table('confluence_page_embeddings',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('page_id', sa.String(length=64), nullable=False),
        sa.Column('embedding', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['page_id'], ['confluence_pages.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_confluence_page_embeddings_page_id'), 'confluence_page_embeddings', ['page_id'], unique=False)
    op.create_index(op.f('ix_confluence_page_embeddings_content_hash'), 'confluence_page_embeddings', ['content_hash'], unique=False)


def downgrade() -> None:
    # Drop confluence_page_embeddings table
    op.drop_index(op.f('ix_confluence_page_embeddings_content_hash'), table_name='confluence_page_embeddings')
    op.drop_index(op.f('ix_confluence_page_embeddings_page_id'), table_name='confluence_page_embeddings')
    op.drop_table('confluence_page_embeddings')
