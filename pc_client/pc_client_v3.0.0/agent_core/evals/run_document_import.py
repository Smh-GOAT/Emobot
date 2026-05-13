import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_core.memory import MemoryStore, import_default_documents, index_missing_embeddings, run_migrations
from agent_core.memory.document_loader import load_default_documents


REQUIRED_QUERIES = ("安装", "烧录", "组装", "固件")


def main():
    parser = argparse.ArgumentParser(description="Import Phase 2.2 project docs into PostgreSQL knowledge chunks.")
    parser.add_argument("--check-only", action="store_true", help="Only load and chunk documents, do not write DB.")
    parser.add_argument("--embed", action="store_true", help="Also generate embeddings for chunks and memories.")
    args = parser.parse_args()

    if args.check_only:
        documents = load_default_documents()
        print(json.dumps({"documents": len(documents)}, ensure_ascii=False))
        return

    run_migrations()
    store = MemoryStore()
    store.healthcheck()
    result = import_default_documents(store)
    embedding_result = None
    if args.embed:
        embedding_result = index_missing_embeddings(store)
    missing = []
    for query in REQUIRED_QUERIES:
        if not store.search_knowledge(query, limit=3):
            missing.append(query)
    if missing:
        raise SystemExit(f"Document import completed, but no chunks matched: {', '.join(missing)}")
    print(
        json.dumps(
            {
                "status": "ok",
                "documents_seen": result.documents_seen,
                "documents_created": result.documents_created,
                "documents_changed": result.documents_changed,
                "chunks_written": result.chunks_written,
                "chunks_skipped": result.chunks_skipped,
                "knowledge_indexed": embedding_result.knowledge_indexed if embedding_result else None,
                "memories_indexed": embedding_result.memories_indexed if embedding_result else None,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
