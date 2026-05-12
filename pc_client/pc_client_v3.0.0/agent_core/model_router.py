from dataclasses import dataclass

from .model_config import (
    FALLBACK_OR_RAG_MAX_TOKENS,
    FALLBACK_OR_RAG_MODEL,
    FALLBACK_OR_RAG_TIMEOUT_SECONDS,
    FAST_CHAT_MAX_TOKENS,
    FAST_CHAT_MODEL,
    FAST_CHAT_TIMEOUT_SECONDS,
)


@dataclass(frozen=True)
class ModelRoute:
    name: str
    model: str
    timeout_seconds: int
    max_tokens: int
    temperature: float
    enable_thinking: bool


FAST_CHAT_ROUTE = ModelRoute(
    name="fast_chat",
    model=FAST_CHAT_MODEL,
    timeout_seconds=FAST_CHAT_TIMEOUT_SECONDS,
    max_tokens=FAST_CHAT_MAX_TOKENS,
    temperature=0.6,
    enable_thinking=False,
)

FALLBACK_OR_RAG_ROUTE = ModelRoute(
    name="fallback_or_rag",
    model=FALLBACK_OR_RAG_MODEL,
    timeout_seconds=FALLBACK_OR_RAG_TIMEOUT_SECONDS,
    max_tokens=FALLBACK_OR_RAG_MAX_TOKENS,
    temperature=0.4,
    enable_thinking=False,
)

ROUTES = {
    FAST_CHAT_ROUTE.name: FAST_CHAT_ROUTE,
    FALLBACK_OR_RAG_ROUTE.name: FALLBACK_OR_RAG_ROUTE,
}


def get_model_route(route_name="fast_chat"):
    return ROUTES.get(route_name, FAST_CHAT_ROUTE)

