import json
import re


ALLOWED_MEMORY_TYPES = {
    "preference",
    "identity",
    "relationship",
    "habit",
    "interaction_style",
    "reminder",
}

SENSITIVE_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"\b\d{15,18}[\dXx]\b"),
    re.compile(r"\b\d{13,19}\b"),
    re.compile(r"(密码|口令|api[ _-]?key|access token|secret|身份证|银行卡|住址|家庭住址|精确定位|医疗诊断|病历)"),
)


def extract_memory_candidate(user_text):
    text = (user_text or "").strip()
    if not text:
        return None
    if contains_sensitive_information(text):
        return _no_memory("包含敏感信息，禁止保存", sensitivity="sensitive")

    preference_markers = ("我喜欢", "我不喜欢", "我爱", "我讨厌")
    identity_markers = ("我叫", "我的名字")
    relationship_markers = ("我的朋友", "我的妈妈", "我的爸爸", "我的猫", "我的狗", "我家")
    style_markers = ("以后叫我", "希望你", "跟我说话", "回复简短", "温柔一点")

    if any(marker in text for marker in preference_markers):
        return {
            "should_remember": True,
            "memory_type": "preference",
            "content": text,
            "confidence": 0.8,
            "sensitivity": "normal",
            "reason": "用户表达了偏好",
        }

    if any(marker in text for marker in identity_markers):
        return {
            "should_remember": True,
            "memory_type": "identity",
            "content": text,
            "confidence": 0.85,
            "sensitivity": "normal",
            "reason": "用户表达了身份信息",
        }

    if any(marker in text for marker in relationship_markers):
        return {
            "should_remember": True,
            "memory_type": "relationship",
            "content": text,
            "confidence": 0.75,
            "sensitivity": "normal",
            "reason": "用户表达了重要关系",
        }

    if any(marker in text for marker in style_markers):
        return {
            "should_remember": True,
            "memory_type": "interaction_style",
            "content": text,
            "confidence": 0.75,
            "sensitivity": "normal",
            "reason": "用户表达了互动风格偏好",
        }

    return _no_memory("没有明确长期记忆信号")


def extract_memory_candidates_with_llm(llm, user_text):
    if not hasattr(llm, "extract_memories"):
        fallback = extract_memory_candidate(user_text)
        return [fallback] if fallback and fallback.get("should_remember") else []
    try:
        raw = llm.extract_memories(user_text)
        data = _parse_json_object(raw)
        candidates = data.get("memories", [])
    except Exception:
        fallback = extract_memory_candidate(user_text)
        return [fallback] if fallback and fallback.get("should_remember") else []

    safe_candidates = []
    for item in candidates:
        normalized = normalize_memory_candidate(item)
        if normalized and normalized.get("should_remember"):
            safe_candidates.append(normalized)
    if safe_candidates:
        return safe_candidates

    fallback = extract_memory_candidate(user_text)
    return [fallback] if fallback and fallback.get("should_remember") else []


def normalize_memory_candidate(item):
    content = str(item.get("content", "")).strip()
    memory_type = str(item.get("memory_type") or item.get("type") or "").strip()
    if not content or memory_type not in ALLOWED_MEMORY_TYPES:
        return None
    if contains_sensitive_information(content):
        return None
    try:
        confidence = float(item.get("confidence", 0.75))
    except (TypeError, ValueError):
        confidence = 0.75
    confidence = min(max(confidence, 0.0), 1.0)
    return {
        "should_remember": True,
        "memory_type": memory_type,
        "content": content,
        "confidence": confidence,
        "sensitivity": "normal",
        "reason": str(item.get("reason", "LLM 记忆抽取")).strip() or "LLM 记忆抽取",
    }


def contains_sensitive_information(text):
    return any(pattern.search(str(text or "")) for pattern in SENSITIVE_PATTERNS)


def classify_memory_command(text):
    normalized = str(text or "").strip()
    lowered = normalized.lower()
    if not normalized:
        return {"command": None, "query": ""}
    name_markers = ("我的名字", "我叫什么", "remember my name", "know my name", "my name")
    if any(marker in lowered for marker in ("do you remember", "what do you remember", "what do you know about me", "show memories", "my memories")):
        query = "name" if any(marker in lowered for marker in name_markers) else ""
        return {"command": "list", "query": query}
    if any(marker in normalized for marker in ("你记得我什么", "你记住了什么", "查看记忆", "我的记忆", "你知道我什么")):
        query = "name" if any(marker in normalized for marker in ("我的名字", "我叫什么")) else ""
        return {"command": "list", "query": query}
    if "忘记" in normalized or "删掉记忆" in normalized or "删除记忆" in normalized or "forget" in lowered or "delete memory" in lowered or "remove memory" in lowered:
        query = normalized
        for marker in (
            "请",
            "帮我",
            "把",
            "这件事",
            "忘记",
            "删掉记忆",
            "删除记忆",
            "关于",
            "please",
            "forget",
            "delete memory",
            "remove memory",
            "about",
        ):
            query = query.replace(marker, "")
        return {"command": "forget", "query": query.strip()}
    return {"command": None, "query": ""}


def _parse_json_object(raw):
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        text = text[start : end + 1]
    return json.loads(text)


def _no_memory(reason, sensitivity="normal"):
    return {
        "should_remember": False,
        "memory_type": None,
        "content": "",
        "confidence": 0,
        "sensitivity": sensitivity,
        "reason": reason,
    }
