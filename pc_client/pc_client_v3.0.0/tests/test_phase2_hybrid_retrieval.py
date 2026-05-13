import unittest

from agent_core import AgentCore, ChatRequest
from agent_core.agent_loop import _classify_retrieval_intent
from agent_core.memory.hybrid_retriever import HybridRetriever


class FakeHybridStore:
    def vector_search_knowledge(self, embedding, limit=5):
        return [
            {
                "id": "k1",
                "title": "固件烧录",
                "content": "固件烧录需要下载固件并使用烧录工具。",
                "metadata": {"source_path": "doc/zh/固件烧录.md"},
                "score": 0.8,
            }
        ]

    def keyword_search_knowledge(self, query, limit=5):
        return [
            {
                "id": "k1",
                "title": "固件烧录",
                "content": "固件烧录需要下载固件并使用烧录工具。",
                "metadata": {"source_path": "doc/zh/固件烧录.md"},
                "score": 0.5,
            }
        ]

    def vector_search_memories(self, user_id, embedding, limit=5):
        return [
            {
                "id": "m1",
                "type": "preference",
                "content": "用户喜欢猫。",
                "metadata": {},
                "score": 0.7,
            }
        ]

    def keyword_search_memories(self, user_id, query, limit=5):
        return []


class FakeEmbeddingClient:
    def embed_text(self, text):
        return [0.1, 0.2, 0.3]


class FakeLLM:
    def __init__(self):
        self.calls = []

    def chat(self, text, route_name="fast_chat", extra_context=None):
        self.calls.append((text, route_name, extra_context))
        return '{"answer":"查到啦","actions":["eye_happy","head_center","eye_blink"]}'


class FakeMemoryStore:
    def __init__(self):
        self.calls = []

    def ensure_user(self, user_id):
        self.calls.append(("ensure_user", user_id))

    def ensure_session(self, session_id, user_id=None, device_id=None, title=None):
        self.calls.append(("ensure_session", session_id, user_id, device_id, title))

    def add_message(self, session_id, role, content, actions=None, model=None, latency_ms=None):
        self.calls.append(("add_message", session_id, role, content))
        return "11111111-1111-1111-1111-111111111111"

    def add_memory(self, user_id, memory_type, content, confidence=0.8, source_message_id=None, metadata=None):
        self.calls.append(("add_memory", user_id, memory_type, content))

    def search_memories(self, user_id, query, limit=5):
        self.calls.append(("search_memories", user_id, query, limit))
        return []


class FakeAgentRetriever:
    def search(self, user_id, query, limit=5, include_knowledge=True, include_memories=True):
        class Result:
            pass

        result = Result()
        result.memories = [
            {
                "type": "preference",
                "content": "用户喜欢猫。",
                "metadata": {},
                "score": 0.9,
            }
        ] if include_memories else []
        result.knowledge = [
            {
                "title": "固件烧录",
                "content": "固件烧录需要下载固件并使用烧录工具。",
                "metadata": {"source_path": "doc/zh/固件烧录.md"},
                "score": 0.9,
            }
        ] if include_knowledge else []
        return result


class Phase24HybridRetrievalTests(unittest.TestCase):
    def test_intent_classifier_keeps_plain_chat_fast(self):
        intent = _classify_retrieval_intent("我今天有点难过")

        self.assertFalse(intent["include_knowledge"])
        self.assertFalse(intent["include_memories"])

    def test_intent_classifier_detects_device_and_memory_queries(self):
        device_intent = _classify_retrieval_intent("怎么给机器人烧录固件")
        memory_intent = _classify_retrieval_intent("你记得我喜欢什么吗")

        self.assertTrue(device_intent["include_knowledge"])
        self.assertFalse(device_intent["include_memories"])
        self.assertTrue(memory_intent["include_memories"])

    def test_hybrid_retriever_merges_vector_and_keyword_scores(self):
        retriever = HybridRetriever(FakeHybridStore(), embedding_client=FakeEmbeddingClient())

        result = retriever.search("local_user", "怎么烧录固件", include_memories=False)

        self.assertEqual(result.knowledge[0]["id"], "k1")
        self.assertGreater(result.knowledge[0]["score"], result.knowledge[0]["keyword_score"])
        self.assertEqual(result.knowledge[0]["metadata"]["source_path"], "doc/zh/固件烧录.md")

    def test_agent_core_injects_hybrid_context_for_device_query(self):
        llm = FakeLLM()
        agent = AgentCore(llm, memory_store=FakeMemoryStore())
        agent._hybrid_retriever = FakeAgentRetriever()

        agent.chat(ChatRequest(text="怎么给机器人烧录固件"))

        extra_context = llm.calls[0][2]
        self.assertIn("# RETRIEVED_DEVICE_KNOWLEDGE", extra_context)
        self.assertIn("doc/zh/固件烧录.md", extra_context)

    def test_agent_core_does_not_trigger_hybrid_context_for_plain_chat(self):
        llm = FakeLLM()
        agent = AgentCore(llm, memory_store=FakeMemoryStore())
        agent._hybrid_retriever = FakeAgentRetriever()

        agent.chat(ChatRequest(text="我今天有点难过"))

        self.assertIsNone(llm.calls[0][2])


if __name__ == "__main__":
    unittest.main()
