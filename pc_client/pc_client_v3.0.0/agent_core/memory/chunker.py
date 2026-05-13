import re
from dataclasses import dataclass, field

from .document_loader import hash_text


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class DocumentChunk:
    title: str
    content: str
    chunk_index: int
    content_hash: str
    metadata: dict = field(default_factory=dict)


def chunk_markdown_document(document, target_chars=900, max_chars=1200, min_chars=120):
    sections = _split_sections(document)
    chunks = []
    pending = []
    pending_title = document.title
    pending_meta = {}

    def flush_pending():
        nonlocal pending, pending_title, pending_meta
        if not pending:
            return
        content = "\n\n".join(pending).strip()
        if content:
            chunks.append((pending_title, content, dict(pending_meta)))
        pending = []
        pending_meta = {}

    for section in sections:
        for piece in _split_large_section(section["content"], target_chars=target_chars, max_chars=max_chars):
            if not pending:
                pending_title = section["title"]
                pending_meta = section["metadata"]
            candidate = "\n\n".join(pending + [piece]).strip()
            if pending and len(candidate) > target_chars and len(candidate) >= min_chars:
                flush_pending()
                pending_title = section["title"]
                pending_meta = section["metadata"]
            pending.append(piece)
            pending_meta = section["metadata"]
            if len("\n\n".join(pending)) >= max_chars:
                flush_pending()
    flush_pending()

    result = []
    seen_hashes = set()
    for index, (title, content, metadata) in enumerate(chunks):
        content_hash = hash_text(content)
        if content_hash in seen_hashes:
            continue
        seen_hashes.add(content_hash)
        result.append(
            DocumentChunk(
                title=title,
                content=content,
                chunk_index=len(result),
                content_hash=content_hash,
                metadata={
                    **document.metadata,
                    **metadata,
                    "source": document.source,
                    "document_hash": document.content_hash,
                    "chunker": "markdown_heading_v1",
                    "target_chars": target_chars,
                    "max_chars": max_chars,
                },
            )
        )
    return result


def _split_sections(document):
    sections = []
    heading_stack = []
    current_lines = []
    current_title = document.title
    current_level = 0

    def flush():
        if not current_lines:
            return
        content = "\n".join(current_lines).strip()
        if not content:
            return
        title_path = " > ".join(heading_stack) if heading_stack else document.title
        sections.append(
            {
                "title": current_title or document.title,
                "content": content,
                "metadata": {
                    "title_path": title_path,
                    "heading_level": current_level,
                },
            }
        )

    for line in document.content.splitlines():
        match = HEADING_RE.match(line.strip())
        if match:
            flush()
            level = len(match.group(1))
            title = match.group(2).strip()
            heading_stack[:] = heading_stack[: level - 1]
            heading_stack.append(title)
            current_lines = [line.strip()]
            current_title = title
            current_level = level
        else:
            current_lines.append(line.rstrip())
    flush()

    if not sections and document.content.strip():
        sections.append(
            {
                "title": document.title,
                "content": document.content.strip(),
                "metadata": {"title_path": document.title, "heading_level": 0},
            }
        )
    return sections


def _split_large_section(content, target_chars, max_chars):
    text = content.strip()
    if len(text) <= max_chars:
        return [text]

    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
    pieces = []
    current = []
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                pieces.append("\n\n".join(current).strip())
                current = []
            pieces.extend(_split_long_paragraph(paragraph, max_chars=max_chars))
            continue
        candidate = "\n\n".join(current + [paragraph]).strip()
        if current and len(candidate) > target_chars:
            pieces.append("\n\n".join(current).strip())
            current = [paragraph]
        else:
            current.append(paragraph)
    if current:
        pieces.append("\n\n".join(current).strip())
    return [piece for piece in pieces if piece]


def _split_long_paragraph(paragraph, max_chars):
    return [paragraph[i : i + max_chars].strip() for i in range(0, len(paragraph), max_chars)]
