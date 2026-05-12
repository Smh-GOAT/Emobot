import json

from .registry import ACTIONS, ALIASES


MAX_ACTIONS = 8
MAX_TOTAL_DURATION_MS = 8000
ENDING_ACTIONS = ["head_center", "eye_blink"]
FALLBACK_RESPONSE = {
    "answer": "我刚刚有点卡住啦，但我还在这儿陪你。",
    "actions": ["wait", "eye_blink", "head_nod", "head_center", "eye_blink"],
}


def canonical_action_name(action):
    if isinstance(action, dict):
        action = action.get("name", "")
    if not isinstance(action, str):
        return ""
    action = action.strip()
    return ALIASES.get(action, action)


def validate_actions(actions):
    sanitized = []
    warnings = []
    total_duration_ms = 0

    if not isinstance(actions, list):
        warnings.append("actions_not_list")
        actions = []

    for raw_action in actions:
        action = canonical_action_name(raw_action)
        spec = ACTIONS.get(action)
        if not spec:
            warnings.append(f"unknown_action:{raw_action}")
            continue
        if len(sanitized) >= MAX_ACTIONS:
            warnings.append("max_actions_exceeded")
            break
        if total_duration_ms + spec.duration_ms > MAX_TOTAL_DURATION_MS:
            warnings.append("max_duration_exceeded")
            break

        sanitized.append(action)
        total_duration_ms += spec.duration_ms

        if spec.requires_center_after and len(sanitized) < MAX_ACTIONS:
            sanitized.append("head_center")
            total_duration_ms += ACTIONS["head_center"].duration_ms

    if not sanitized:
        sanitized = FALLBACK_RESPONSE["actions"][:]
        warnings.append("fallback_actions_used")

    if sanitized[-2:] != ENDING_ACTIONS:
        while sanitized and sanitized[-1] in ENDING_ACTIONS:
            sanitized.pop()
        if len(sanitized) > MAX_ACTIONS - len(ENDING_ACTIONS):
            sanitized = sanitized[: MAX_ACTIONS - len(ENDING_ACTIONS)]
        sanitized.extend(ENDING_ACTIONS)

    return sanitized[:MAX_ACTIONS], warnings


def normalize_response(raw_response):
    warnings = []
    try:
        data = json.loads(raw_response) if isinstance(raw_response, str) else raw_response
    except (TypeError, json.JSONDecodeError):
        data = FALLBACK_RESPONSE.copy()
        warnings.append("invalid_json")

    if not isinstance(data, dict):
        data = FALLBACK_RESPONSE.copy()
        warnings.append("response_not_object")

    answer = data.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        answer = FALLBACK_RESPONSE["answer"]
        warnings.append("missing_answer")

    actions, action_warnings = validate_actions(data.get("actions"))
    warnings.extend(action_warnings)

    normalized = {
        "answer": answer.strip(),
        "actions": actions,
    }
    return normalized, warnings
