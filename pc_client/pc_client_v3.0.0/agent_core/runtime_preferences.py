import os

from .config import load_env


SUPPORTED_REPLY_LANGUAGES = {
    "zh": "中文",
    "en": "English",
}

_reply_language = None


def get_reply_language():
    if _reply_language:
        return _reply_language
    load_env()
    return normalize_reply_language(os.getenv("EMOBOT_REPLY_LANGUAGE", "zh"))


def set_reply_language(language):
    global _reply_language
    _reply_language = normalize_reply_language(language)
    return _reply_language


def normalize_reply_language(language):
    value = str(language or "").strip().lower()
    if value in ("english", "en-us", "en_us"):
        return "en"
    if value in ("chinese", "中文", "zh-cn", "zh_cn", "cn"):
        return "zh"
    return value if value in SUPPORTED_REPLY_LANGUAGES else "zh"


def get_reply_language_label():
    return SUPPORTED_REPLY_LANGUAGES[get_reply_language()]


def build_reply_language_prompt():
    language = get_reply_language()
    if language == "en":
        return (
            "# RUNTIME_REPLY_LANGUAGE\n\n"
            "Reply in English for this session. Every sentence in the user-facing answer must be English, except for proper names that are originally written in another language.\n"
            "Keep Emobot's existing personality, emotional support style, and safety boundaries.\n"
            "Do not translate tool/action names; only the user-facing answer should be English.\n"
            "If other prompt sections contain Chinese examples or Chinese policy text, treat them as behavior guidance only, not as the reply language."
        )
    return (
        "# RUNTIME_REPLY_LANGUAGE\n\n"
        "本轮会话默认使用中文回复。\n"
        "保持 Emobot 现有的人格、情绪支持方式和安全边界。"
    )


def build_reply_language_user_instruction():
    if get_reply_language() == "en":
        return (
            "\n## Runtime language override\n"
            "The answer field MUST be in English only. Do not answer in Chinese. "
            "Chinese proper names may stay in Chinese characters.\n\n"
        )
    return "\n## Runtime language override\nanswer 字段必须使用中文。\n\n"
