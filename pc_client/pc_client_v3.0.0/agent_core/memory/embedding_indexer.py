from dataclasses import dataclass

from .embedding_client import EmbeddingClient


@dataclass(frozen=True)
class EmbeddingIndexResult:
    knowledge_indexed: int = 0
    memories_indexed: int = 0


def index_missing_embeddings(memory_store, embedding_client=None, limit=100, batch_size=10):
    client = embedding_client or EmbeddingClient()
    knowledge_indexed = index_missing_knowledge_embeddings(
        memory_store,
        embedding_client=client,
        limit=limit,
        batch_size=batch_size,
    )
    memories_indexed = index_missing_memory_embeddings(
        memory_store,
        embedding_client=client,
        limit=limit,
        batch_size=batch_size,
    )
    return EmbeddingIndexResult(
        knowledge_indexed=knowledge_indexed,
        memories_indexed=memories_indexed,
    )


def index_missing_knowledge_embeddings(memory_store, embedding_client=None, limit=100, batch_size=10):
    client = embedding_client or EmbeddingClient()
    chunks = memory_store.list_knowledge_chunks_without_embedding(limit=limit)
    texts = [chunk.content for chunk in chunks]
    embeddings = client.embed_texts(texts, batch_size=batch_size) if texts else []
    for chunk, embedding in zip(chunks, embeddings):
        memory_store.set_knowledge_chunk_embedding(chunk.id, embedding, model=client.model)
    return len(embeddings)


def index_missing_memory_embeddings(memory_store, embedding_client=None, limit=100, batch_size=10):
    client = embedding_client or EmbeddingClient()
    memories = memory_store.list_memories_without_embedding(limit=limit)
    texts = [memory.content for memory in memories]
    embeddings = client.embed_texts(texts, batch_size=batch_size) if texts else []
    for memory, embedding in zip(memories, embeddings):
        memory_store.set_memory_embedding(memory.id, embedding, model=client.model)
    return len(embeddings)
