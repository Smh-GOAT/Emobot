import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ChatRequest:
    text: str
    session_id: str = "default"
    user_id: str = "local_user"
    context: Dict[str, Any] = field(default_factory=dict)
    route: str = "fast_chat"


@dataclass
class ChatResponse:
    answer: str
    actions: List[str]
    warnings: List[str] = field(default_factory=list)
    route: str = "fast_chat"
    model: Optional[str] = None
    latency_ms: Optional[int] = None
    raw_response: Optional[str] = None

    def to_payload(self):
        return {
            "answer": self.answer,
            "actions": self.actions,
        }

    def to_json(self):
        return json.dumps(self.to_payload(), ensure_ascii=False)

    def to_debug_dict(self):
        return asdict(self)

