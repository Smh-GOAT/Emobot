from dataclasses import dataclass

from .embedding_client import EmbeddingClient


@dataclass(frozen=True)
class RetrievalResult:
    memories: list
    knowledge: list


class HybridRetriever:
    def __init__(self, store, embedding_client=None, vector_weight=0.7, keyword_weight=0.3):
        self.store = store
        self.embedding_client = embedding_client or EmbeddingClient()
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

    def search(self, user_id, query, limit=5, include_knowledge=True, include_memories=True):
        embedding = self.embedding_client.embed_text(query)
        memories = []
        knowledge = []
        if include_memories:
            memories = self._merge_hits(
                vector_hits=self.store.vector_search_memories(user_id, embedding, limit=limit * 2),
                keyword_hits=self.store.keyword_search_memories(user_id, query, limit=limit * 2),
                limit=limit,
                kind="memory",
            )
        if include_knowledge:
            knowledge = self._merge_hits(
                vector_hits=self.store.vector_search_knowledge(embedding, limit=limit * 2),
                keyword_hits=self.store.keyword_search_knowledge(query, limit=limit * 2),
                limit=limit,
                kind="knowledge",
            )
        return RetrievalResult(memories=memories, knowledge=knowledge)

    def _merge_hits(self, vector_hits, keyword_hits, limit, kind):
        merged = {}
        for hit in vector_hits:
            key = str(hit["id"])
            item = merged.setdefault(key, self._base_hit(hit, kind))
            item["vector_score"] = float(hit.get("score") or 0)
        for hit in keyword_hits:
            key = str(hit["id"])
            item = merged.setdefault(key, self._base_hit(hit, kind))
            item["keyword_score"] = float(hit.get("score") or 0)
        for item in merged.values():
            item["score"] = (
                self.vector_weight * item.get("vector_score", 0)
                + self.keyword_weight * item.get("keyword_score", 0)
            )
        return sorted(merged.values(), key=lambda item: item["score"], reverse=True)[:limit]

    def _base_hit(self, hit, kind):
        result = {
            "id": str(hit["id"]),
            "kind": kind,
            "content": hit.get("content", ""),
            "metadata": hit.get("metadata") or {},
            "vector_score": 0.0,
            "keyword_score": 0.0,
        }
        if kind == "knowledge":
            result["title"] = hit.get("title")
        else:
            result["type"] = hit.get("type")
        return result
