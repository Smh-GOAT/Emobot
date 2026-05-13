import unittest

from agent_core.config import get_embedding_config
from agent_core.memory.embedding_indexer import index_missing_embeddings
from agent_core.memory.store import _format_vector
from agent_core.memory.vector_search import VectorSearch


class FakeItem:
    def __init__(self, item_id, content):
        self.id = item_id
        self.content = content


class FakeEmbeddingClient:
    model = "fake-embedding"

    def __init__(self):
        self.calls = []

    def embed_texts(self, texts, batch_size=16):
        self.calls.append(("embed_texts", list(texts), batch_size))
        return [[float(index), 0.1, 0.2] for index, _ in enumerate(texts, start=1)]

    def embed_text(self, text):
        self.calls.append(("embed_text", text))
        return [0.9, 0.1, 0.2]


class FakeEmbeddingStore:
    def __init__(self):
        self.knowledge = [FakeItem("chunk-1", "固件烧录说明")]
        self.memories = [FakeItem("memory-1", "用户喜欢猫")]
        self.set_calls = []
        self.vector_calls = []

    def list_knowledge_chunks_without_embedding(self, limit=100):
        return self.knowledge[:limit]

    def list_memories_without_embedding(self, limit=100):
        return self.memories[:limit]

    def set_knowledge_chunk_embedding(self, chunk_id, embedding, model=None):
        self.set_calls.append(("knowledge", chunk_id, embedding, model))
        return True

    def set_memory_embedding(self, memory_id, embedding, model=None):
        self.set_calls.append(("memory", memory_id, embedding, model))
        return True

    def vector_search_knowledge(self, embedding, limit=5):
        self.vector_calls.append(("knowledge", embedding, limit))
        return [{"id": "chunk-1", "content": "固件烧录说明", "score": 0.9}]

    def vector_search_memories(self, user_id, embedding, limit=5):
        self.vector_calls.append(("memory", user_id, embedding, limit))
        return [{"id": "memory-1", "content": "用户喜欢猫", "score": 0.9}]


class Phase23EmbeddingTests(unittest.TestCase):
    def test_embedding_config_reads_env_shape(self):
        config = get_embedding_config()

        self.assertIn("api_url", config)
        self.assertIn("api_key", config)
        self.assertIn("model", config)
        self.assertIn("dim", config)

    def test_format_vector_outputs_pgvector_literal(self):
        self.assertEqual(_format_vector([0.1, 2, -3.5]), "[0.1,2,-3.5]")

    def test_index_missing_embeddings_writes_knowledge_and_memory_vectors(self):
        store = FakeEmbeddingStore()
        client = FakeEmbeddingClient()

        result = index_missing_embeddings(store, embedding_client=client, limit=10, batch_size=4)

        self.assertEqual(result.knowledge_indexed, 1)
        self.assertEqual(result.memories_indexed, 1)
        self.assertEqual(len(store.set_calls), 2)
        self.assertTrue(all(call[3] == "fake-embedding" for call in store.set_calls))

    def test_vector_search_embeds_query_before_store_search(self):
        store = FakeEmbeddingStore()
        client = FakeEmbeddingClient()
        search = VectorSearch(store, embedding_client=client)

        knowledge = search.search_knowledge("怎么烧录固件", limit=3)
        memories = search.search_memories("local_user", "我喜欢什么动物", limit=2)

        self.assertEqual(knowledge[0]["id"], "chunk-1")
        self.assertEqual(memories[0]["id"], "memory-1")
        self.assertIn(("embed_text", "怎么烧录固件"), client.calls)
        self.assertIn(("knowledge", [0.9, 0.1, 0.2], 3), store.vector_calls)


if __name__ == "__main__":
    unittest.main()
