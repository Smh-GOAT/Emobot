import hashlib
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_DOCUMENT_PATHS = (
    "README.md",
    "README_zh.md",
    "doc/zh/软件手册.md",
    "doc/zh/固件烧录.md",
    "doc/zh/组装教程.md",
    "firmware/README.md",
)


@dataclass(frozen=True)
class SourceDocument:
    source: str
    title: str
    content: str
    content_hash: str
    metadata: dict = field(default_factory=dict)


def get_project_root():
    return Path(__file__).resolve().parents[4]


def load_default_documents(project_root=None):
    return load_markdown_documents(DEFAULT_DOCUMENT_PATHS, project_root=project_root)


def load_markdown_documents(paths, project_root=None):
    root = Path(project_root or get_project_root()).resolve()
    documents = []
    for item in paths:
        path = (root / item).resolve()
        if root not in path.parents and path != root:
            raise ValueError(f"Document path is outside project root: {item}")
        if not path.exists():
            raise FileNotFoundError(path)
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            continue
        source = path.relative_to(root).as_posix()
        documents.append(
            SourceDocument(
                source=source,
                title=_extract_title(content, fallback=path.stem),
                content=content,
                content_hash=hash_text(content),
                metadata={
                    "source_path": source,
                    "file_name": path.name,
                    "loader": "markdown",
                },
            )
        )
    return documents


def hash_text(text):
    normalized = "\n".join(line.rstrip() for line in str(text).strip().splitlines())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _extract_title(content, fallback):
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            if title:
                return title
    return fallback
