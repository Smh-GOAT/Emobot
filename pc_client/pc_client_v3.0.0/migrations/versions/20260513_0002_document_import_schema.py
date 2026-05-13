"""add document import metadata

Revision ID: 20260513_0002
Revises: 20260512_0001
Create Date: 2026-05-13
"""
from alembic import op


revision = "20260513_0002"
down_revision = "20260512_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS content_hash TEXT")
    op.execute("ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now()")
    op.execute("ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS content_hash TEXT")
    op.execute("ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS chunk_index INTEGER")
    op.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_documents_source ON knowledge_documents (source)")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_chunks_doc_hash
        ON knowledge_chunks (document_id, content_hash)
        WHERE content_hash IS NOT NULL
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_document_id ON knowledge_chunks (document_id)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_knowledge_chunks_document_id")
    op.execute("DROP INDEX IF EXISTS idx_knowledge_chunks_doc_hash")
    op.execute("DROP INDEX IF EXISTS idx_knowledge_documents_source")
    op.execute("ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS chunk_index")
    op.execute("ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS content_hash")
    op.execute("ALTER TABLE knowledge_documents DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE knowledge_documents DROP COLUMN IF EXISTS content_hash")
