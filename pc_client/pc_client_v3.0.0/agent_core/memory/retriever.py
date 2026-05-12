class MemoryRetriever:
    def __init__(self, store):
        self.store = store

    def search(self, user_id, query, limit=5):
        memories = self.store.search_memories(user_id=user_id, query=query, limit=limit)
        knowledge = self.store.search_knowledge(query=query, limit=limit)
        return {
            "memories": [
                {"id": str(memory.id), "type": memory.type, "content": memory.content}
                for memory in memories
            ],
            "knowledge": [
                {"id": str(chunk.id), "title": chunk.title, "content": chunk.content}
                for chunk in knowledge
            ],
        }

