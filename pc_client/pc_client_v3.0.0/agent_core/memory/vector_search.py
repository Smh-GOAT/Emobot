from .embedding_client import EmbeddingClient


class VectorSearch:
    def __init__(self, store, embedding_client=None):
        self.store = store
        self.embedding_client = embedding_client or EmbeddingClient()

    def search_knowledge(self, query, limit=5):
        embedding = self.embedding_client.embed_text(query)
        return self.store.vector_search_knowledge(embedding, limit=limit)

    def search_memories(self, user_id, query, limit=5):
        embedding = self.embedding_client.embed_text(query)
        return self.store.vector_search_memories(user_id, embedding, limit=limit)
