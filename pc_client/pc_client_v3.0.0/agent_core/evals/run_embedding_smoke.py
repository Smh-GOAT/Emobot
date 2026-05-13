import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_core.memory import MemoryStore, VectorSearch, import_default_documents, index_missing_embeddings, run_migrations


def main():
    run_migrations()
    store = MemoryStore()
    store.healthcheck()
    import_default_documents(store)
    store.ensure_user("local_user")
    if not store.search_memories("local_user", "猫", limit=1):
        store.add_memory("local_user", "preference", "用户喜欢猫，也喜欢温柔简短的回答。")
    indexed = index_missing_embeddings(store)

    search = VectorSearch(store)
    knowledge = search.search_knowledge("怎么给机器人刷系统", limit=5)
    memories = search.search_memories("local_user", "我喜欢什么动物", limit=5)

    if not any(("烧录" in row["content"] or "固件" in row["content"]) for row in knowledge):
        raise SystemExit("Expected vector search to retrieve firmware flashing knowledge.")
    if not any("猫" in row["content"] for row in memories):
        raise SystemExit("Expected vector search to retrieve cat preference memory.")

    print(
        json.dumps(
            {
                "status": "ok",
                "knowledge_indexed": indexed.knowledge_indexed,
                "memories_indexed": indexed.memories_indexed,
                "knowledge_hits": len(knowledge),
                "memory_hits": len(memories),
                "top_knowledge_score": knowledge[0]["score"] if knowledge else None,
                "top_memory_score": memories[0]["score"] if memories else None,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
