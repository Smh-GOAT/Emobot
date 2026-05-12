import unittest

from agent_core import AgentCore, ChatRequest
from agent_core.config import normalize_database_url
from agent_core.memory.extractor import extract_memory_candidate


class FakeLLM:
    def chat(self, text, route_name="fast_chat"):
        return '{"answer":"记住啦主人","actions":["love","eye_happy","head_center","eye_blink"]}'


class FakeMemoryStore:
    def __init__(self):
        self.calls = []

    def ensure_user(self, user_id):
        self.calls.append(("ensure_user", user_id))

    def ensure_session(self, session_id, user_id=None, device_id=None, title=None):
        self.calls.append(("ensure_session", session_id, user_id, device_id, title))

    def add_message(self, session_id, role, content, actions=None, model=None, latency_ms=None):
        self.calls.append(("add_message", session_id, role, content, actions, model))
        return "11111111-1111-1111-1111-111111111111"

    def add_memory(self, user_id, memory_type, content, confidence=0.8, source_message_id=None, metadata=None):
        self.calls.append(("add_memory", user_id, memory_type, content, confidence, source_message_id, metadata))


class Phase2MemoryTests(unittest.TestCase):
    def test_database_url_uses_psycopg_driver(self):
        self.assertEqual(
            normalize_database_url("postgresql://u:p@localhost:5433/emobot"),
            "postgresql+psycopg://u:p@localhost:5433/emobot",
        )

    def test_memory_extractor_detects_preference(self):
        candidate = extract_memory_candidate("我喜欢猫")

        self.assertTrue(candidate["should_remember"])
        self.assertEqual(candidate["memory_type"], "preference")

    def test_agent_core_persists_messages_and_memory_when_store_is_present(self):
        store = FakeMemoryStore()
        response = AgentCore(FakeLLM(), memory_store=store).chat(ChatRequest(text="我喜欢猫"))

        self.assertEqual(response.answer, "记住啦主人")
        self.assertTrue(any(call[0] == "add_message" and call[2] == "user" for call in store.calls))
        self.assertTrue(any(call[0] == "add_message" and call[2] == "assistant" for call in store.calls))
        self.assertTrue(any(call[0] == "add_memory" for call in store.calls))


if __name__ == "__main__":
    unittest.main()

