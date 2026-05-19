import inspect
import re
import time

from .actions import normalize_response, validate_actions
from .memory.extractor import classify_memory_command, extract_memory_candidates_with_llm
from .memory.hybrid_retriever import HybridRetriever
from .model_router import get_model_route
from .runtime_preferences import get_reply_language
from .schemas import ChatRequest, ChatResponse


class AgentCore:
    def __init__(self, llm, memory_store=None):
        self.llm = llm
        self.memory_store = memory_store
        self._hybrid_retriever = None

    def chat(self, request):
        if isinstance(request, str):
            request = ChatRequest(text=request)

        route = get_model_route(request.route)
        user_message_id = self._save_user_message(request)
        memory_command_response = self._handle_memory_command(request, route)
        if memory_command_response:
            self._save_assistant_message(request, memory_command_response)
            return memory_command_response
        memory_context = self._build_memory_context(request)
        start_time = time.perf_counter()
        try:
            raw_response = self._call_llm(request.text, route.name, memory_context)
            normalized, warnings = normalize_response(raw_response)
        except Exception as exc:
            raw_response = None
            normalized, warnings = normalize_response(None)
            warnings.append(f"llm_error:{type(exc).__name__}")

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        response = ChatResponse(
            answer=normalized["answer"],
            actions=normalized["actions"],
            warnings=warnings,
            route=route.name,
            model=route.model,
            latency_ms=latency_ms,
            raw_response=raw_response,
        )
        self._save_assistant_message(request, response)
        self._extract_memory(request, user_message_id)
        return response

    def _save_user_message(self, request):
        if not self.memory_store or not request.text:
            return None
        try:
            self.memory_store.ensure_user(request.user_id)
            self.memory_store.ensure_session(
                request.session_id,
                user_id=request.user_id,
                device_id=request.context.get("device_id"),
                title=request.text[:40],
            )
            return self.memory_store.add_message(
                session_id=request.session_id,
                role="user",
                content=request.text,
            )
        except Exception:
            return None

    def _save_assistant_message(self, request, response):
        if not self.memory_store or not request.text:
            return
        try:
            self.memory_store.add_message(
                session_id=request.session_id,
                role="assistant",
                content=response.answer,
                actions=response.actions,
                model=response.model,
                latency_ms=response.latency_ms,
            )
        except Exception:
            return

    def _extract_memory(self, request, source_message_id):
        if not self.memory_store or not source_message_id:
            return
        candidates = extract_memory_candidates_with_llm(self.llm, request.text)
        if not candidates:
            return
        for candidate in candidates:
            try:
                self.memory_store.add_memory(
                    user_id=request.user_id,
                    memory_type=candidate["memory_type"],
                    content=candidate["content"],
                    confidence=candidate["confidence"],
                    source_message_id=source_message_id,
                    metadata={
                        "reason": candidate["reason"],
                        "extractor": "llm_or_rule",
                    },
                )
            except Exception:
                continue

    def _handle_memory_command(self, request, route):
        if not self.memory_store or not request.text:
            return None
        command = classify_memory_command(request.text)
        if command["command"] == "list":
            try:
                memories = self.memory_store.list_memories(request.user_id, limit=10)
            except Exception:
                return None
            answer = _format_memory_list_answer(memories, query=command["query"])
            return _direct_response(answer, route)
        if command["command"] == "forget":
            query = command["query"]
            if not query:
                return _direct_response(_localized_text(
                    zh="可以，但请告诉我要忘记哪件事。",
                    en="Sure, but please tell me what you want me to forget.",
                ), route)
            try:
                deleted = self.memory_store.delete_memories_by_query(request.user_id, query, limit=10)
            except Exception:
                return None
            if deleted:
                answer = _localized_text(
                    zh="好，我已经忘记这件事了。",
                    en="Okay, I've forgotten that.",
                )
            else:
                answer = _localized_text(
                    zh="我没找到对应记忆，可以说得更具体一点。",
                    en="I couldn't find that memory. Could you be more specific?",
                )
            return _direct_response(answer, route)
        return None

    def _build_memory_context(self, request):
        if not self.memory_store or not request.text:
            return None
        retrieval_context = self._build_retrieval_context(request)
        if retrieval_context:
            return retrieval_context
        try:
            memories = self.memory_store.search_memories(request.user_id, request.text, limit=5)
        except Exception:
            return None
        if not memories:
            return None
        lines = [
            "以下是可用于个性化陪伴的用户长期记忆。只在自然相关时使用，不要机械复述，不要泄露为系统信息。"
        ]
        for memory in memories:
            lines.append(f"- [{memory.type}] {memory.content}")
        return "\n".join(lines)

    def _build_retrieval_context(self, request):
        intent = _classify_retrieval_intent(request.text)
        if not intent["include_knowledge"] and not intent["include_memories"]:
            return None
        try:
            retriever = self._get_hybrid_retriever()
            result = retriever.search(
                request.user_id,
                request.text,
                limit=4,
                include_knowledge=intent["include_knowledge"],
                include_memories=intent["include_memories"],
            )
        except Exception:
            return None
        lines = []
        if result.memories:
            lines.append("# RETRIEVED_LONG_TERM_MEMORIES")
            lines.append("以下是检索到的用户长期记忆。只在自然相关时使用，不要机械复述。")
            for item in result.memories:
                lines.append(f"- [{item.get('type')}] {item['content']}")
        if result.knowledge:
            lines.append("# RETRIEVED_DEVICE_KNOWLEDGE")
            lines.append("以下是从项目说明文档检索到的资料。回答设备/软件/固件问题时优先基于这些内容；资料不足时说明不确定。")
            for item in result.knowledge:
                title = item.get("title") or "未命名片段"
                source = (item.get("metadata") or {}).get("source_path") or (item.get("metadata") or {}).get("source")
                source_note = f" source={source}" if source else ""
                lines.append(f"- [{title}{source_note}] {item['content']}")
        return "\n".join(lines) if lines else None

    def _get_hybrid_retriever(self):
        if self._hybrid_retriever is None:
            self._hybrid_retriever = HybridRetriever(self.memory_store)
        return self._hybrid_retriever

    def _call_llm(self, text, route_name, extra_context=None):
        parameters = inspect.signature(self.llm.chat).parameters
        if "extra_context" in parameters:
            return self.llm.chat(text, route_name=route_name, extra_context=extra_context)
        return self.llm.chat(text, route_name=route_name)

    def action_payload(self, action):
        actions, warnings = validate_actions([action])
        return ChatResponse(
            answer="",
            actions=actions,
            warnings=warnings,
            route="manual_action",
        )


KNOWLEDGE_QUERY_TERMS = (
    "怎么",
    "如何",
    "说明",
    "文档",
    "帮助",
    "安装",
    "启动",
    "运行",
    "连接",
    "串口",
    "蓝牙",
    "usb",
    "api",
    "key",
    "固件",
    "烧录",
    "刷机",
    "升级",
    "组装",
    "舵机",
    "wifi",
    "wi-fi",
    "重置",
    "上位机",
    "esp32",
    "机器人",
)

MEMORY_QUERY_TERMS = (
    "记得",
    "记住",
    "忘记",
    "我喜欢",
    "我不喜欢",
    "我的名字",
    "我叫什么",
    "我是谁",
    "偏好",
    "remember",
    "memory",
    "memories",
    "forget",
    "my name",
    "know my name",
    "what do you know",
)


def _classify_retrieval_intent(text):
    lowered = str(text or "").lower()
    return {
        "include_knowledge": any(term in lowered for term in KNOWLEDGE_QUERY_TERMS),
        "include_memories": any(term in lowered for term in MEMORY_QUERY_TERMS),
    }


def _direct_response(answer, route):
    return ChatResponse(
        answer=answer,
        actions=["eye_happy", "head_center", "eye_blink"],
        warnings=[],
        route=route.name,
        model=route.model,
        latency_ms=0,
        raw_response=None,
    )


def _format_memory_list_answer(memories, query=""):
    filtered = list(memories)
    if query == "name":
        filtered = [
            memory
            for memory in filtered
            if memory.type == "identity"
            or "我叫" in memory.content
            or "名字" in memory.content
            or "call me" in memory.content.lower()
            or "my name" in memory.content.lower()
        ]
    if not filtered:
        return _localized_text(
            zh="我现在还没有记住你的名字。" if query == "name" else "我现在还没有长期记忆。",
            en="I don't have your name in memory yet." if query == "name" else "I don't have any long-term memories yet.",
        )
    if query == "name":
        if get_reply_language() == "en":
            return _format_name_memory_en(filtered[0].content)
        return _format_name_memory_zh(filtered[0].content)
    snippets = [_clean_memory_for_reply(memory.content) for memory in filtered[:5]]
    if get_reply_language() == "en":
        return "I remember: " + "; ".join(snippets)
    return "我记得：" + "；".join(snippets)


def _localized_text(zh, en):
    return en if get_reply_language() == "en" else zh


def _format_name_memory_en(content):
    name, nickname = _extract_name_parts(content)
    if name and nickname and nickname != name:
        return f"Yes, I remember. Your name is {name}, and I can call you {nickname}."
    if name:
        return f"Yes, I remember. Your name is {name}."
    return "Yes, I remember your name, but I only have it stored in my original note."


def _format_name_memory_zh(content):
    name, nickname = _extract_name_parts(content)
    if name and nickname and nickname != name:
        return f"我记得，你叫{name}，我可以叫你{nickname}。"
    if name:
        return f"我记得，你叫{name}。"
    return "我记得你的名字，但这条记忆还需要整理一下。"


def _extract_name_parts(content):
    text = str(content or "").strip()
    name = _first_match(text, (r"我叫([^，,。；;\s]+)", r"my name is\s+([^,.。；;]+)", r"call me\s+([^,.。；;]+)"))
    nickname = _first_match(text, (r"叫我([^，,。；;\s]+)", r"call me\s+([^,.。；;]+)"))
    return name, nickname


def _first_match(text, patterns):
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _clean_memory_for_reply(content):
    text = str(content or "").strip()
    replacements = (
        ("用户希望", "你希望"),
        ("用户喜欢", "你喜欢"),
        ("用户不喜欢", "你不喜欢"),
        ("用户的", "你的"),
        ("用户", "你"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text
