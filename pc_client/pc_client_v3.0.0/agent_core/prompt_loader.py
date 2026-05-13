from pathlib import Path


PROMPT_ASSET_DIR = Path(__file__).with_name("prompt_assets")
PROMPT_ASSET_ORDER = (
    "SAFETY_BOUNDARY.md",
    "IDENTITY.md",
    "SOUL.md",
    "EMOTIONAL_SUPPORT_POLICY.md",
)
SOUL_PROMPT_NAME = "SOUL.md"


def load_prompt_asset(name):
    path = _safe_asset_path(name)
    return path.read_text(encoding="utf-8").strip()


def save_soul_prompt(content):
    text = str(content or "").strip()
    if not text:
        raise ValueError("SOUL.md content cannot be empty")
    _safe_asset_path(SOUL_PROMPT_NAME).write_text(text + "\n", encoding="utf-8")


def load_soul_prompt():
    return load_prompt_asset(SOUL_PROMPT_NAME)


def build_role_prompt(extra_context=None):
    sections = [load_prompt_asset(name) for name in PROMPT_ASSET_ORDER]
    if extra_context:
        sections.append("# DYNAMIC_CONTEXT\n\n" + str(extra_context).strip())
    return "\n\n---\n\n".join(section for section in sections if section).strip()


def _safe_asset_path(name):
    path = (PROMPT_ASSET_DIR / name).resolve()
    asset_dir = PROMPT_ASSET_DIR.resolve()
    if asset_dir not in path.parents or path.name != name:
        raise ValueError(f"Invalid prompt asset name: {name}")
    if not path.exists():
        raise FileNotFoundError(path)
    return path
