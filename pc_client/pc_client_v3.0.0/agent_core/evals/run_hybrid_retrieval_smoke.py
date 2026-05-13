import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_core import AgentCore, ChatRequest
from agent_core.memory import HybridRetriever, MemoryStore, import_default_documents, index_missing_embeddings, run_migrations


class CaptureLLM:
    def __init__(self):
        self.calls = []

    def chat(self, text, route_name="fast_chat", extra_context=None):
        self.calls.append({"text": text, "route_name": route_name, "extra_context": extra_context})
        return '{"answer":"可以，我查到固件烧录说明了。","actions":["eye_happy","head_center","eye_blink"]}'


def main():
    run_migrations()
    store = MemoryStore()
    store.healthcheck()
    import_default_documents(store)
    index_missing_embeddings(store)

    retriever = HybridRetriever(store)
    result = retriever.search("local_user", "怎么给机器人刷系统", limit=5, include_memories=False)
    if not any(("烧录" in item["content"] or "固件" in item["content"]) for item in result.knowledge):
        raise SystemExit("Expected hybrid retrieval to recall firmware/flashing knowledge.")

    llm = CaptureLLM()
    agent = AgentCore(llm, memory_store=store)
    agent.chat(ChatRequest(text="怎么给机器人刷系统"))
    extra_context = llm.calls[0]["extra_context"]
    if not extra_context or "# RETRIEVED_DEVICE_KNOWLEDGE" not in extra_context:
        raise SystemExit("Expected AgentCore to inject retrieved device knowledge.")

    print(
        json.dumps(
            {
                "status": "ok",
                "knowledge_hits": len(result.knowledge),
                "top_score": result.knowledge[0]["score"] if result.knowledge else None,
                "agent_context_injected": True,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
