import tempfile
import unittest
from pathlib import Path

from agent_core.memory.chunker import chunk_markdown_document
from agent_core.memory.document_importer import import_documents
from agent_core.memory.document_loader import SourceDocument, hash_text, load_markdown_documents


class FakeDocumentStore:
    def __init__(self):
        self.documents = {}
        self.chunks = {}

    def upsert_knowledge_document(self, source, title=None, metadata=None, content_hash=None):
        existing = self.documents.get(source)
        if not existing:
            self.documents[source] = {
                "id": source,
                "title": title,
                "metadata": metadata,
                "content_hash": content_hash,
            }
            return source, True, True
        changed = existing["content_hash"] != content_hash
        existing.update(title=title, metadata=metadata, content_hash=content_hash)
        return source, False, changed

    def replace_knowledge_chunks(self, document_id, chunks):
        self.chunks[document_id] = list(chunks)
        return len(chunks)


class Phase22DocumentImportTests(unittest.TestCase):
    def test_loader_reads_markdown_documents_with_hash_and_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "doc.md").write_text("# 软件手册\n\n## 安装\n\n先启动上位机。", encoding="utf-8")

            documents = load_markdown_documents(["doc.md"], project_root=root)

        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].source, "doc.md")
        self.assertEqual(documents[0].title, "软件手册")
        self.assertEqual(documents[0].content_hash, hash_text(documents[0].content))

    def test_chunker_preserves_title_path_and_hashes(self):
        document = SourceDocument(
            source="doc/zh/软件手册.md",
            title="软件手册",
            content="# 软件手册\n\n## 安装\n\n先安装 Python。\n\n## 使用\n\n刷新串口后点击连接。",
            content_hash="doc-hash",
            metadata={"source_path": "doc/zh/软件手册.md"},
        )

        chunks = chunk_markdown_document(document, target_chars=80, max_chars=120)

        self.assertGreaterEqual(len(chunks), 1)
        self.assertTrue(all(chunk.content_hash for chunk in chunks))
        self.assertTrue(any("title_path" in chunk.metadata for chunk in chunks))
        self.assertEqual(chunks[0].chunk_index, 0)

    def test_import_documents_is_idempotent_when_hash_is_unchanged(self):
        store = FakeDocumentStore()
        document = SourceDocument(
            source="README_zh.md",
            title="Emobot",
            content="# Emobot\n\n## 启动\n\n运行 start.sh。",
            content_hash="same-hash",
            metadata={"source_path": "README_zh.md"},
        )

        first = import_documents(store, [document])
        second = import_documents(store, [document])

        self.assertEqual(first.documents_created, 1)
        self.assertGreater(first.chunks_written, 0)
        self.assertEqual(second.documents_created, 0)
        self.assertEqual(second.documents_changed, 0)
        self.assertEqual(second.chunks_written, 0)
        self.assertGreater(second.chunks_skipped, 0)


if __name__ == "__main__":
    unittest.main()
