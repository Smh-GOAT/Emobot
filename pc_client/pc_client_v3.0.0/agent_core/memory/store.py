import uuid
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
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

    def add_knowledge_document(self, source, title=None, metadata=None):
        doc = KnowledgeDocument(source=source, title=title, metadata_json=metadata or {})
        with self.SessionLocal.begin() as db:
            db.add(doc)
        return doc.id

    def add_knowledge_chunk(self, document_id, content, title=None, metadata=None):
        chunk = KnowledgeChunk(
            document_id=_coerce_uuid(document_id),
            title=title,
            content=content,
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


def _coerce_uuid(value):
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(value))
