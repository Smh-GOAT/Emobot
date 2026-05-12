import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import declarative_base
from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **kw):
        return "vector"


Base = declarative_base()


def uuid_column():
    return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class User(Base):
    __tablename__ = "users"

    id = uuid_column()
    display_name = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Device(Base):
    __tablename__ = "devices"

    id = uuid_column()
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    name = Column(Text)
    firmware_version = Column(Text)
    metadata_json = Column("metadata", JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Session(Base):
    __tablename__ = "sessions"

    id = uuid_column()
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"))
    title = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Message(Base):
    __tablename__ = "messages"

    id = uuid_column()
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"))
    role = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    actions = Column(JSONB)
    model = Column(Text)
    latency_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Memory(Base):
    __tablename__ = "memories"

    id = uuid_column()
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    type = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False, server_default="0.8")
    source_message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"))
    metadata_json = Column("metadata", JSONB, nullable=False, server_default="{}")
    embedding = Column(Vector)
    search_tsv = Column(TSVECTOR)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_used_at = Column(DateTime(timezone=True))
    deleted_at = Column(DateTime(timezone=True))


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = uuid_column()
    source = Column(Text, nullable=False)
    title = Column(Text)
    metadata_json = Column("metadata", JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = uuid_column()
    document_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_documents.id"))
    title = Column(Text)
    content = Column(Text, nullable=False)
    metadata_json = Column("metadata", JSONB, nullable=False, server_default="{}")
    embedding = Column(Vector)
    search_tsv = Column(TSVECTOR)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SkillInvocation(Base):
    __tablename__ = "skill_invocations"

    id = uuid_column()
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"))
    skill_name = Column(Text, nullable=False)
    input = Column(JSONB, nullable=False, server_default="{}")
    output = Column(JSONB)
    status = Column(Text, nullable=False)
    latency_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ActionLog(Base):
    __tablename__ = "action_logs"

    id = uuid_column()
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"))
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"))
    actions = Column(JSONB, nullable=False)
    status = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

