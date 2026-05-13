import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_core import AgentCore, ChatRequest
from agent_core.memory import MemoryStore, run_migrations


class FakeMemoryLLM:
    def __init__(self):
        self.chat_calls = []
        self.extract_calls = []

    def chat(self, text, route_name="fast_chat", extra_context=None):
        self.chat_calls.append((text, route_name, extra_context))
        return '{"answer":"我记住啦。","actions":["eye_happy","head_center","eye_blink"]}'

    def extract_memories(self, user_text):
        self.extract_calls.append(user_text)
        return (
            '{"memories":[{"memory_type":"interaction_style",'
            '"content":"用户希望 Emobot 回答简短温柔。",'
            '"confidence":0.86,"reason":"用户表达了互动风格偏好"}]}'
        )


def main():
    run_migrations()
    store = MemoryStore()
    store.healthcheck()
    store.ensure_user("local_user")
    store.add_memory("local_user", "preference", "用户喜欢猫。", metadata={"source": "phase25_smoke"})

    llm = FakeMemoryLLM()
    agent = AgentCore(llm, memory_store=store)

    list_response = agent.chat(ChatRequest(text="你记得我什么"))
    if "用户喜欢猫" not in list_response.answer:
        raise SystemExit("Expected memory list response to include cat preference.")

    forget_response = agent.chat(ChatRequest(text="忘记我喜欢猫"))
    if "已经忘记" not in forget_response.answer:
        raise SystemExit("Expected forget response to confirm deletion.")

    agent.chat(ChatRequest(text="以后回答我简短温柔一点"))
    remembered = store.search_memories("local_user", "简短温柔", limit=5)
    if not remembered:
        raise SystemExit("Expected LLM memory extraction to save interaction style.")

    print(
        json.dumps(
            {
                "status": "ok",
                "list_answer": list_response.answer,
                "forget_answer": forget_response.answer,
                "extracted_memories": len(remembered),
                "llm_extract_calls": len(llm.extract_calls),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
