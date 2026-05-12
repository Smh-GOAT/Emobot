import time

from .actions import normalize_response, validate_actions
from .memory.extractor import extract_memory_candidate
from .model_router import get_model_route
from .schemas import ChatRequest, ChatResponse


class AgentCore:
    def __init__(self, llm, memory_store=None):
        self.llm = llm
        self.memory_store = memory_store

    def chat(self, request):
        if isinstance(request, str):
            request = ChatRequest(text=request)

        route = get_model_route(request.route)
        user_message_id = self._save_user_message(request)
        start_time = time.perf_counter()
        try:
            raw_response = self.llm.chat(request.text, route_name=route.name)
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
        candidate = extract_memory_candidate(request.text)
        if not candidate or not candidate.get("should_remember"):
            return
        try:
            self.memory_store.add_memory(
                user_id=request.user_id,
                memory_type=candidate["memory_type"],
                content=candidate["content"],
                confidence=candidate["confidence"],
                source_message_id=source_message_id,
                metadata={"reason": candidate["reason"]},
            )
        except Exception:
            return

    def action_payload(self, action):
        actions, warnings = validate_actions([action])
        return ChatResponse(
            answer="",
            actions=actions,
            warnings=warnings,
            route="manual_action",
        )
