import json
import uuid
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, delete, func, or_, select, text
from sqlalchemy.orm import sessionmaker

from agent_core.config import get_database_url
from .models import (
    Device,
    KnowledgeChunk,
    KnowledgeDocument,
    Memory,
    Message,
    Session,
    User,
)


def _database_url(database_url=None):
    url = database_url or get_database_url()
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url


def make_engine(database_url=None):
    return create_engine(_database_url(database_url), pool_pre_ping=True)


def run_migrations(database_url=None):
    project_dir = Path(__file__).resolve().parents[2]
    config = Config(str(project_dir / "alembic.ini"))
    config.set_main_option("script_location", str(project_dir / "migrations"))
    config.set_main_option("sqlalchemy.url", _database_url(database_url))
    command.upgrade(config, "head")


class MemoryStore:
    def __init__(self, database_url=None):
        self.engine = make_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

    def healthcheck(self):
        with self.engine.connect() as conn:
            return conn.execute(text("SELECT 1")).scalar_one()

    def ensure_user(self, user_id, display_name=None):
        user_uuid = _coerce_uuid(user_id)
        with self.SessionLocal.begin() as db:
            user = db.get(User, user_uuid)
            if not user:
                user = User(id=user_uuid, display_name=display_name)
                db.add(user)
            elif display_name and user.display_name != display_name:
                user.display_name = display_name
        return user_uuid

    def ensure_device(self, device_id, user_id=None, name=None, firmware_version=None):
        device_uuid = _coerce_uuid(device_id)
        user_uuid = _coerce_uuid(user_id) if user_id else None
        with self.SessionLocal.begin() as db:
            device = db.get(Device, device_uuid)
            if not device:
                device = Device(
                    id=device_uuid,
                    user_id=user_uuid,
                    name=name,
                    firmware_version=firmware_version,
                )
                db.add(device)
            else:
                if user_uuid:
                    device.user_id = user_uuid
                if name:
                    device.name = name
                if firmware_version:
                    device.firmware_version = firmware_version
        return device_uuid

    def ensure_session(self, session_id, user_id=None, device_id=None, title=None):
        session_uuid = _coerce_uuid(session_id)
        user_uuid = _coerce_uuid(user_id) if user_id else None
        device_uuid = _coerce_uuid(device_id) if device_id else None
        with self.SessionLocal.begin() as db:
            session = db.get(Session, session_uuid)
            if not session:
                session = Session(
                    id=session_uuid,
                    user_id=user_uuid,
                    device_id=device_uuid,
                    title=title,
                )
                db.add(session)
            else:
                if title and not session.title:
                    session.title = title
        return session_uuid

    def add_message(self, session_id, role, content, actions=None, model=None, latency_ms=None):
        message = Message(
            session_id=_coerce_uuid(session_id),
            role=role,
            content=content,
            actions=actions,
            model=model,
            latency_ms=latency_ms,
        )
        with self.SessionLocal.begin() as db:
            db.add(message)
        return message.id

    def add_memory(self, user_id, memory_type, content, confidence=0.8, source_message_id=None, metadata=None):
        existing = self.find_similar_memory(user_id, content)
        if existing:
            self.update_memory(
                existing.id,
                memory_type=memory_type,
                content=content,
                confidence=max(float(existing.confidence or 0), confidence),
                metadata={**(existing.metadata_json or {}), **(metadata or {})},
            )
            return existing.id
        memory = Memory(
            user_id=_coerce_uuid(user_id),
            type=memory_type,
            content=content,
            confidence=confidence,
            source_message_id=_coerce_uuid(source_message_id) if source_message_id else None,
            metadata_json=metadata or {},
        )
        with self.SessionLocal.begin() as db:
            db.add(memory)
        return memory.id

    def find_similar_memory(self, user_id, content):
        with self.SessionLocal() as db:
            stmt = (
                select(Memory)
                .where(Memory.user_id == _coerce_uuid(user_id))
                .where(Memory.deleted_at.is_(None))
                .where(Memory.content == content)
                .limit(1)
            )
            return db.scalars(stmt).first()

    def search_memories(self, user_id, query, limit=5):
        with self.SessionLocal() as db:
            stmt = (
                select(Memory)
                .where(Memory.user_id == _coerce_uuid(user_id))
                .where(Memory.deleted_at.is_(None))
                .where(Memory.content.ilike(f"%{query}%"))
                .order_by(Memory.updated_at.desc())
                .limit(limit)
            )
            return list(db.scalars(stmt))

    def list_memories(self, user_id, limit=50):
        with self.SessionLocal() as db:
            stmt = (
                select(Memory)
                .where(Memory.user_id == _coerce_uuid(user_id))
                .where(Memory.deleted_at.is_(None))
                .order_by(Memory.updated_at.desc())
                .limit(limit)
            )
            return list(db.scalars(stmt))

    def delete_memories_by_query(self, user_id, query, limit=10):
        if not str(query or "").strip():
            return 0
        tokens = _memory_query_tokens(query)
        filters = [Memory.content.ilike(f"%{token}%") for token in tokens]
        with self.SessionLocal.begin() as db:
            stmt = (
                select(Memory)
                .where(Memory.user_id == _coerce_uuid(user_id))
                .where(Memory.deleted_at.is_(None))
                .where(or_(*filters))
                .order_by(Memory.updated_at.desc())
                .limit(limit)
            )
            memories = list(db.scalars(stmt))
            for memory in memories:
                memory.deleted_at = func.now()
                memory.updated_at = func.now()
            return len(memories)

    def update_memory(self, memory_id, memory_type=None, content=None, confidence=None, metadata=None):
        memory_uuid = _coerce_uuid(memory_id)
        with self.SessionLocal.begin() as db:
            memory = db.get(Memory, memory_uuid)
            if not memory or memory.deleted_at is not None:
                return False
            if memory_type:
                memory.type = memory_type
            if content:
                memory.content = content
            if confidence is not None:
                memory.confidence = confidence
            if metadata is not None:
                memory.metadata_json = metadata
            memory.updated_at = func.now()
        return True

    def delete_memory(self, memory_id):
        memory_uuid = _coerce_uuid(memory_id)
        with self.SessionLocal.begin() as db:
            memory = db.get(Memory, memory_uuid)
            if not memory or memory.deleted_at is not None:
                return False
            memory.deleted_at = func.now()
            memory.updated_at = func.now()
        return True

    def add_knowledge_document(self, source, title=None, metadata=None, content_hash=None):
        doc = KnowledgeDocument(
            source=source,
            title=title,
            content_hash=content_hash,
            metadata_json=metadata or {},
        )
        with self.SessionLocal.begin() as db:
            db.add(doc)
        return doc.id

    def upsert_knowledge_document(self, source, title=None, metadata=None, content_hash=None):
        with self.SessionLocal.begin() as db:
            stmt = select(KnowledgeDocument).where(KnowledgeDocument.source == source).limit(1)
            doc = db.scalars(stmt).first()
            created = False
            changed = False
            if not doc:
                doc = KnowledgeDocument(
                    source=source,
                    title=title,
                    content_hash=content_hash,
                    metadata_json=metadata or {},
                )
                db.add(doc)
                created = True
                changed = True
            else:
                changed = bool(content_hash and doc.content_hash != content_hash)
                if title:
                    doc.title = title
                if metadata is not None:
                    doc.metadata_json = metadata
                if content_hash:
                    doc.content_hash = content_hash
                doc.updated_at = func.now()
        return doc.id, created, changed

    def replace_knowledge_chunks(self, document_id, chunks):
        document_uuid = _coerce_uuid(document_id)
        with self.SessionLocal.begin() as db:
            db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_uuid))
            for chunk in chunks:
                db.add(
                    KnowledgeChunk(
                        document_id=document_uuid,
                        title=chunk.title,
                        content=chunk.content,
                        content_hash=chunk.content_hash,
                        chunk_index=chunk.chunk_index,
                        metadata_json=chunk.metadata,
                    )
                )
        return len(chunks)

    def count_knowledge_chunks(self, document_id):
        with self.SessionLocal() as db:
            stmt = select(func.count()).select_from(KnowledgeChunk).where(
                KnowledgeChunk.document_id == _coerce_uuid(document_id)
            )
            return db.execute(stmt).scalar_one()

    def add_knowledge_chunk(
        self,
        document_id,
        content,
        title=None,
        metadata=None,
        content_hash=None,
        chunk_index=None,
    ):
        chunk = KnowledgeChunk(
            document_id=_coerce_uuid(document_id),
            title=title,
            content=content,
            content_hash=content_hash,
            chunk_index=chunk_index,
            metadata_json=metadata or {},
        )
        with self.SessionLocal.begin() as db:
            db.add(chunk)
        return chunk.id

    def search_knowledge(self, query, limit=5):
        with self.SessionLocal() as db:
            stmt = (
                select(KnowledgeChunk)
                .where(KnowledgeChunk.content.ilike(f"%{query}%"))
                .order_by(KnowledgeChunk.created_at.desc())
                .limit(limit)
            )
            return list(db.scalars(stmt))

    def keyword_search_knowledge(self, query, limit=5):
        pattern = f"%{query}%"
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    WITH q AS (
                        SELECT websearch_to_tsquery('simple', :query) AS query
                    )
                    SELECT
                        kc.id,
                        kc.title,
                        kc.content,
                        kc.metadata,
                        CASE
                            WHEN q.query <> ''::tsquery THEN
                                ts_rank_cd(
                                    to_tsvector('simple', coalesce(kc.title, '') || ' ' || kc.content),
                                    q.query
                                )
                            ELSE 0
                        END
                        + CASE
                            WHEN kc.content ILIKE :pattern OR coalesce(kc.title, '') ILIKE :pattern THEN 0.5
                            ELSE 0
                          END AS score
                    FROM knowledge_chunks kc, q
                    WHERE
                        (q.query <> ''::tsquery AND to_tsvector('simple', coalesce(kc.title, '') || ' ' || kc.content) @@ q.query)
                        OR kc.content ILIKE :pattern
                        OR coalesce(kc.title, '') ILIKE :pattern
                    ORDER BY score DESC, kc.created_at DESC
                    LIMIT :limit
                    """
                ),
                {"query": query, "pattern": pattern, "limit": limit},
            ).mappings()
            return [dict(row) for row in rows]

    def keyword_search_memories(self, user_id, query, limit=5):
        pattern = f"%{query}%"
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    WITH q AS (
                        SELECT websearch_to_tsquery('simple', :query) AS query
                    )
                    SELECT
                        id,
                        type,
                        content,
                        metadata,
                        CASE
                            WHEN q.query <> ''::tsquery THEN
                                ts_rank_cd(to_tsvector('simple', content), q.query)
                            ELSE 0
                        END
                        + CASE WHEN content ILIKE :pattern THEN 0.5 ELSE 0 END AS score
                    FROM memories, q
                    WHERE user_id = CAST(:user_id AS uuid)
                      AND deleted_at IS NULL
                      AND (
                        (q.query <> ''::tsquery AND to_tsvector('simple', content) @@ q.query)
                        OR content ILIKE :pattern
                      )
                    ORDER BY score DESC, updated_at DESC
                    LIMIT :limit
                    """
                ),
                {
                    "user_id": str(_coerce_uuid(user_id)),
                    "query": query,
                    "pattern": pattern,
                    "limit": limit,
                },
            ).mappings()
            return [dict(row) for row in rows]

    def list_knowledge_chunks_without_embedding(self, limit=100):
        with self.SessionLocal() as db:
            stmt = (
                select(KnowledgeChunk)
                .where(KnowledgeChunk.embedding.is_(None))
                .order_by(KnowledgeChunk.created_at.asc(), KnowledgeChunk.chunk_index.asc())
                .limit(limit)
            )
            return list(db.scalars(stmt))

    def list_memories_without_embedding(self, limit=100):
        with self.SessionLocal() as db:
            stmt = (
                select(Memory)
                .where(Memory.embedding.is_(None))
                .where(Memory.deleted_at.is_(None))
                .order_by(Memory.created_at.asc())
                .limit(limit)
            )
            return list(db.scalars(stmt))

    def set_knowledge_chunk_embedding(self, chunk_id, embedding, model=None):
        return self._set_embedding(
            table="knowledge_chunks",
            item_id=chunk_id,
            embedding=embedding,
            metadata={"embedding_model": model} if model else {},
        )

    def set_memory_embedding(self, memory_id, embedding, model=None):
        return self._set_embedding(
            table="memories",
            item_id=memory_id,
            embedding=embedding,
            metadata={"embedding_model": model} if model else {},
        )

    def vector_search_knowledge(self, embedding, limit=5):
        vector = _format_vector(embedding)
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, title, content, metadata, 1 - (embedding <=> CAST(:embedding AS vector)) AS score
                    FROM knowledge_chunks
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> CAST(:embedding AS vector)
                    LIMIT :limit
                    """
                ),
                {"embedding": vector, "limit": limit},
            ).mappings()
            return [dict(row) for row in rows]

    def vector_search_memories(self, user_id, embedding, limit=5):
        vector = _format_vector(embedding)
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, type, content, metadata, 1 - (embedding <=> CAST(:embedding AS vector)) AS score
                    FROM memories
                    WHERE user_id = CAST(:user_id AS uuid)
                      AND deleted_at IS NULL
                      AND embedding IS NOT NULL
                    ORDER BY embedding <=> CAST(:embedding AS vector)
                    LIMIT :limit
                    """
                ),
                {"user_id": str(_coerce_uuid(user_id)), "embedding": vector, "limit": limit},
            ).mappings()
            return [dict(row) for row in rows]

    def _set_embedding(self, table, item_id, embedding, metadata=None):
        if table not in {"knowledge_chunks", "memories"}:
            raise ValueError(f"Unsupported embedding table: {table}")
        vector = _format_vector(embedding)
        metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
        with self.engine.begin() as conn:
            result = conn.execute(
                text(
                    f"""
                    UPDATE {table}
                    SET embedding = CAST(:embedding AS vector),
                        metadata = metadata || CAST(:metadata AS jsonb)
                    WHERE id = CAST(:id AS uuid)
                    """
                ),
                {
                    "id": str(_coerce_uuid(item_id)),
                    "embedding": vector,
                    "metadata": metadata_json,
                },
            )
            return result.rowcount > 0


def _coerce_uuid(value):
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(value))


def _format_vector(embedding):
    values = [float(value) for value in embedding]
    if not values:
        raise ValueError("Embedding vector cannot be empty")
    return "[" + ",".join(f"{value:.12g}" for value in values) + "]"


def _memory_query_tokens(query):
    text_value = str(query or "").strip()
    for token in ("我", "的", "喜欢", "不喜欢", "记忆", "事情", "这件", "关于"):
        text_value = text_value.replace(token, " ")
    tokens = [token.strip() for token in text_value.split() if len(token.strip()) >= 1]
    if tokens:
        return tokens
    return [str(query or "").strip()]
