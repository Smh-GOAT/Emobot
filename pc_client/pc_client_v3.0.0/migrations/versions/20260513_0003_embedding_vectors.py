"""fix embedding vector dimensions

Revision ID: 20260513_0003
Revises: 20260513_0002
Create Date: 2026-05-13
"""
from alembic import op


revision = "20260513_0003"
down_revision = "20260513_0002"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("ALTER TABLE memories ALTER COLUMN embedding TYPE vector(1024) USING embedding::vector(1024)")
    op.execute("ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector(1024) USING embedding::vector(1024)")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_embedding_cosine
        ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 10)
        WHERE embedding IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_memories_embedding_cosine
        ON memories USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 10)
        WHERE embedding IS NOT NULL
        """
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_memories_embedding_cosine")
    op.execute("DROP INDEX IF EXISTS idx_knowledge_chunks_embedding_cosine")
    op.execute("ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector USING embedding::vector")
    op.execute("ALTER TABLE memories ALTER COLUMN embedding TYPE vector USING embedding::vector")
