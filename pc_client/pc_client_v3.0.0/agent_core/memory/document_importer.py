from dataclasses import dataclass

from .chunker import chunk_markdown_document
from .document_loader import load_default_documents


@dataclass(frozen=True)
class ImportResult:
    documents_seen: int
    documents_created: int
    documents_changed: int
    chunks_written: int
    chunks_skipped: int


def import_default_documents(memory_store, project_root=None):
    documents = load_default_documents(project_root=project_root)
    return import_documents(memory_store, documents)


def import_documents(memory_store, documents):
    created_count = 0
    changed_count = 0
    chunks_written = 0
    chunks_skipped = 0

    for document in documents:
        chunks = chunk_markdown_document(document)
        document_id, created, changed = memory_store.upsert_knowledge_document(
            source=document.source,
            title=document.title,
            content_hash=document.content_hash,
            metadata={
                **document.metadata,
                "phase": "2.2",
                "chunk_count": len(chunks),
            },
        )
        if created:
            created_count += 1
        needs_chunk_refresh = changed
        if not needs_chunk_refresh and hasattr(memory_store, "count_knowledge_chunks"):
            needs_chunk_refresh = memory_store.count_knowledge_chunks(document_id) != len(chunks)
        if needs_chunk_refresh:
            changed_count += 1
            chunks_written += memory_store.replace_knowledge_chunks(document_id, chunks)
        else:
            chunks_skipped += len(chunks)

    return ImportResult(
        documents_seen=len(documents),
        documents_created=created_count,
        documents_changed=changed_count,
        chunks_written=chunks_written,
        chunks_skipped=chunks_skipped,
    )
