import unittest
from importlib.util import find_spec

from agent_core import AgentCore, ChatRequest, ChatResponse
from agent_core.model_router import get_model_route


class FakeLLM:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def chat(self, text, route_name="fast_chat"):
        self.calls.append((text, route_name))
        return self.response


class Phase1AgentCoreTests(unittest.TestCase):
    def test_agent_core_returns_chat_response(self):
        llm = FakeLLM('{"answer":"你好呀主人","actions":["heart","eye_happy","head_center","eye_blink"]}')
        agent = AgentCore(llm)

        response = agent.chat(ChatRequest(text="你好"))

        self.assertIsInstance(response, ChatResponse)
        self.assertEqual(response.answer, "你好呀主人")
        self.assertEqual(response.route, "fast_chat")
        self.assertEqual(llm.calls, [("你好", "fast_chat")])

    def test_agent_core_falls_back_on_llm_error(self):
        class BrokenLLM:
            def chat(self, text, route_name="fast_chat"):
                raise RuntimeError("boom")

        response = AgentCore(BrokenLLM()).chat("你好")

        self.assertIn("llm_error:RuntimeError", response.warnings)
        self.assertIn("answer", response.to_payload())

    def test_model_router_has_phase1_routes(self):
        fast = get_model_route("fast_chat")
        fallback = get_model_route("fallback_or_rag")

        self.assertEqual(fast.model, "qwen3.6-flash")
        self.assertEqual(fallback.model, "deepseek-v4-flash")

    def test_gpt_compat_entrypoint_reexports_agent_core_client(self):
        if find_spec("openai") is None:
            self.skipTest("openai package is not installed in this Python environment")
        from agent_core.llm_client import GPT
        from gpt import GPT as CompatGPT

        self.assertIs(CompatGPT, GPT)


if __name__ == "__main__":
    unittest.main()
