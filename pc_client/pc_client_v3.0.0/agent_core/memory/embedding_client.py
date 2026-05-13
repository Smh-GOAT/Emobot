from openai import OpenAI

from agent_core.config import get_embedding_config


class EmbeddingClient:
    def __init__(self, api_url=None, api_key=None, model=None, dim=None, timeout=30):
        config = get_embedding_config()
        self.api_url = api_url or config["api_url"]
        self.api_key = api_key or config["api_key"]
        self.model = model or config["model"]
        self.dim = dim or config["dim"]
        self.timeout = timeout
        if not self.api_url or not self.api_key or not self.model:
            raise RuntimeError("EMBEDDING_API_URL, EMBEDDING_API_KEY and EMBEDDING_MODEL must be configured")
        self.client = OpenAI(base_url=self.api_url, api_key=self.api_key, timeout=self.timeout)

    def embed_text(self, text):
        return self.embed_texts([text])[0]

    def embed_texts(self, texts, batch_size=10):
        embeddings = []
        clean_texts = [str(text or "").strip() for text in texts]
        for start in range(0, len(clean_texts), batch_size):
            batch = clean_texts[start : start + batch_size]
            response = self.client.embeddings.create(model=self.model, input=batch)
            batch_embeddings = [item.embedding for item in response.data]
            for embedding in batch_embeddings:
                self._validate_embedding(embedding)
            embeddings.extend(batch_embeddings)
        return embeddings

    def _validate_embedding(self, embedding):
        if not embedding:
            raise RuntimeError("Embedding API returned an empty vector")
        if self.dim and len(embedding) != self.dim:
            raise RuntimeError(f"Embedding dimension mismatch: expected {self.dim}, got {len(embedding)}")
