import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_core.memory import MemoryRetriever, MemoryStore, run_migrations


def main():
    run_migrations()
    store = MemoryStore()
    store.healthcheck()
    store.ensure_user("local_user", display_name="Local User")
    store.ensure_session("default", user_id="local_user", title="memory smoke")
    message_id = store.add_message("default", "user", "我喜欢猫")
    store.add_memory("local_user", "preference", "用户喜欢猫", source_message_id=message_id)
    doc_id = store.add_knowledge_document("smoke", title="测试文档")
    store.add_knowledge_chunk(doc_id, "串口连接需要先刷新端口再点击连接。", title="串口连接")
    result = MemoryRetriever(store).search("local_user", "猫", limit=5)

    if not result["memories"]:
        raise SystemExit("Expected at least one memory search result.")
    print("Phase 2 memory smoke OK")


if __name__ == "__main__":
    main()
