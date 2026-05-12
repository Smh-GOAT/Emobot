def extract_memory_candidate(user_text):
    text = (user_text or "").strip()
    if not text:
        return None

    preference_markers = ("我喜欢", "我不喜欢", "我爱", "我讨厌")
    identity_markers = ("我叫", "我的名字")

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

    return {
        "should_remember": False,
        "memory_type": None,
        "content": "",
        "confidence": 0,
        "sensitivity": "normal",
        "reason": "没有明确长期记忆信号",
    }

