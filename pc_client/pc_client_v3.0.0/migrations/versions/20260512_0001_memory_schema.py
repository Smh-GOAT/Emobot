"""create memory schema

Revision ID: 20260512_0001
Revises:
Create Date: 2026-05-12
"""
from alembic import op


revision = "20260512_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
          id UUID PRIMARY KEY,
          display_name TEXT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS devices (
          id UUID PRIMARY KEY,
          user_id UUID REFERENCES users(id),
          name TEXT,
          firmware_version TEXT,
          metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
          id UUID PRIMARY KEY,
          user_id UUID REFERENCES users(id),
          device_id UUID REFERENCES devices(id),
          title TEXT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
          id UUID PRIMARY KEY,
          session_id UUID REFERENCES sessions(id),
          role TEXT NOT NULL,
          content TEXT NOT NULL,
          actions JSONB,
          model TEXT,
          latency_ms INTEGER,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS memories (
          id UUID PRIMARY KEY,
          user_id UUID REFERENCES users(id),
          type TEXT NOT NULL,
          content TEXT NOT NULL,
          confidence REAL NOT NULL DEFAULT 0.8,
          source_message_id UUID REFERENCES messages(id),
          metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
          embedding vector,
          search_tsv tsvector,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          last_used_at TIMESTAMPTZ,
          deleted_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_documents (
          id UUID PRIMARY KEY,
          source TEXT NOT NULL,
          title TEXT,
          metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_chunks (
          id UUID PRIMARY KEY,
          document_id UUID REFERENCES knowledge_documents(id),
          title TEXT,
          content TEXT NOT NULL,
          metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
          embedding vector,
          search_tsv tsvector,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS skill_invocations (
          id UUID PRIMARY KEY,
          session_id UUID REFERENCES sessions(id),
          skill_name TEXT NOT NULL,
          input JSONB NOT NULL DEFAULT '{}'::jsonb,
          output JSONB,
          status TEXT NOT NULL,
          latency_ms INTEGER,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS action_logs (
          id UUID PRIMARY KEY,
          session_id UUID REFERENCES sessions(id),
          device_id UUID REFERENCES devices(id),
          actions JSONB NOT NULL,
          status TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_memories_search_tsv ON memories USING GIN (search_tsv)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_search_tsv ON knowledge_chunks USING GIN (search_tsv)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS action_logs")
    op.execute("DROP TABLE IF EXISTS skill_invocations")
    op.execute("DROP TABLE IF EXISTS knowledge_chunks")
    op.execute("DROP TABLE IF EXISTS knowledge_documents")
    op.execute("DROP TABLE IF EXISTS memories")
    op.execute("DROP TABLE IF EXISTS messages")
    op.execute("DROP TABLE IF EXISTS sessions")
    op.execute("DROP TABLE IF EXISTS devices")
    op.execute("DROP TABLE IF EXISTS users")

