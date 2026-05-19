import unittest

from agent_core import AgentCore, ChatRequest
from agent_core.memory.extractor import (
    classify_memory_command,
    contains_sensitive_information,
    extract_memory_candidates_with_llm,
)
from agent_core.runtime_preferences import set_reply_language


class FakeMemory:
    def __init__(self, content, memory_type="preference"):
        self.content = content
        self.type = memory_type
        self.id = "memory-1"
        self.confidence = 0.8
        self.metadata_json = {}


class FakeLLMExtractor:
    def __init__(self, raw):
        self.raw = raw

    def extract_memories(self, user_text):
        return self.raw


class FakeChatLLM:
    def __init__(self):
        self.calls = []

    def chat(self, text, route_name="fast_chat", extra_context=None):
        self.calls.append((text, route_name, extra_context))
        return '{"answer":"好呀","actions":["eye_happy","head_center","eye_blink"]}'


class FakeMemoryStore:
    def __init__(self):
        self.memories = [FakeMemory("用户喜欢猫，也喜欢温柔简短的回答。")]
        self.calls = []

    def ensure_user(self, user_id):
        self.calls.append(("ensure_user", user_id))

    def ensure_session(self, session_id, user_id=None, device_id=None, title=None):
        self.calls.append(("ensure_session", session_id, user_id, device_id, title))

    def add_message(self, session_id, role, content, actions=None, model=None, latency_ms=None):
        self.calls.append(("add_message", role, content))
        return "11111111-1111-1111-1111-111111111111"

    def list_memories(self, user_id, limit=50):
        return self.memories[:limit]

    def delete_memories_by_query(self, user_id, query, limit=10):
        self.calls.append(("delete_memories_by_query", user_id, query, limit))
        before = len(self.memories)
        self.memories = [memory for memory in self.memories if query not in memory.content and "猫" not in memory.content]
        return before - len(self.memories)

    def search_memories(self, user_id, query, limit=5):
        return []

    def add_memory(self, user_id, memory_type, content, confidence=0.8, source_message_id=None, metadata=None):
        self.calls.append(("add_memory", memory_type, content, metadata))


class Phase25MemoryManagementTests(unittest.TestCase):
    def test_sensitive_information_is_not_remembered(self):
        self.assertTrue(contains_sensitive_information("我的 API key 是 sk-abcdefghijklmnopqrstuvwxyz"))

        candidates = extract_memory_candidates_with_llm(
            FakeLLMExtractor(
                '{"memories":[{"memory_type":"identity","content":"用户的 API key 是 sk-abcdefghijklmnopqrstuvwxyz","confidence":0.9}]}'
            ),
            "我的 API key 是 sk-abcdefghijklmnopqrstuvwxyz",
        )

        self.assertEqual(candidates, [])

    def test_llm_memory_extractor_accepts_safe_structured_memory(self):
        candidates = extract_memory_candidates_with_llm(
            FakeLLMExtractor(
                '{"memories":[{"memory_type":"interaction_style","content":"用户希望回答简短温柔。","confidence":0.82,"reason":"互动风格偏好"}]}'
            ),
            "以后回答我简短温柔一点",
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["memory_type"], "interaction_style")

    def test_memory_command_classifier_detects_list_and_forget(self):
        self.assertEqual(classify_memory_command("你记得我什么")["command"], "list")
        self.assertEqual(classify_memory_command("Do you remember my name?")["command"], "list")
        self.assertEqual(classify_memory_command("Do you remember my name?")["query"], "name")
        forget = classify_memory_command("请忘记我喜欢猫")

        self.assertEqual(forget["command"], "forget")
        self.assertIn("猫", forget["query"])

    def test_agent_core_lists_memories_without_calling_llm(self):
        llm = FakeChatLLM()
        store = FakeMemoryStore()
        response = AgentCore(llm, memory_store=store).chat(ChatRequest(text="你记得我什么"))

        self.assertIn("你喜欢猫", response.answer)
        self.assertEqual(llm.calls, [])
        self.assertTrue(any(call[0] == "add_message" and call[1] == "assistant" for call in store.calls))

    def test_agent_core_forgets_matching_memory_without_calling_llm(self):
        llm = FakeChatLLM()
        store = FakeMemoryStore()
        response = AgentCore(llm, memory_store=store).chat(ChatRequest(text="忘记我喜欢猫"))

        self.assertIn("已经忘记", response.answer)
        self.assertEqual(llm.calls, [])
        self.assertEqual(store.memories, [])

    def test_agent_core_answers_english_memory_command_in_english(self):
        try:
            set_reply_language("en")
            llm = FakeChatLLM()
            store = FakeMemoryStore()
            store.memories = [FakeMemory("我叫沈墨涵，你可以叫我墨涵。", "identity")]

            response = AgentCore(llm, memory_store=store).chat(ChatRequest(text="Do you remember my name?"))

            self.assertIn("Yes, I remember", response.answer)
            self.assertIn("Your name is", response.answer)
            self.assertIn("沈墨涵", response.answer)
            self.assertIn("墨涵", response.answer)
            self.assertNotIn("我叫", response.answer)
            self.assertEqual(llm.calls, [])
        finally:
            set_reply_language("zh")


if __name__ == "__main__":
    unittest.main()
