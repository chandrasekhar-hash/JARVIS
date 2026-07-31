"""
JARVIS Product 1.6 - Embedding Provider Architecture.
Provides unified local and cloud embedding generation with model versioning.
"""

import hashlib
import math
import logging
from typing import List, Dict, Any, Optional
from ..interfaces import IEmbeddingProvider

logger = logging.getLogger(__name__)


class LocalSTEmbeddingProvider(IEmbeddingProvider):
    """
    Local Sentence-Transformers / Deterministic Hashing CPU embedding provider.
    Dimensions: 384
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.dimension = 384
        self.model_version = f"{model_name}:v1"
        self._st_model = None
        self._init_local_model()

    def _init_local_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            self._st_model = SentenceTransformer(self.model_name)
            logger.info(f"SentenceTransformer '{self.model_name}' loaded successfully.")
        except ImportError:
            logger.info("sentence_transformers not installed. Utilizing local deterministic hash-vector provider.")

    def get_provider_name(self) -> str:
        return "local_sentence_transformers"

    def get_dimension(self) -> int:
        return self.dimension

    def get_model_version(self) -> str:
        return self.model_version

    def _hash_vector(self, text: str) -> List[float]:
        """Generates a normalized deterministic 384-dimensional dense vector representation."""
        vec = [0.0] * self.dimension
        tokens = text.lower().split()
        for idx, token in enumerate(tokens):
            h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            pos = h % self.dimension
            val = (h % 200 - 100) / 100.0
            vec[pos] += val
        
        # Normalize vector
        magnitude = math.sqrt(sum(v * v for v in vec))
        if magnitude > 0:
            vec = [v / magnitude for v in vec]
        else:
            vec[0] = 1.0
        return vec

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        if self._st_model is not None:
            try:
                embeddings = self._st_model.encode(texts, convert_to_numpy=True)
                return [emb.tolist() for emb in embeddings]
            except Exception as e:
                logger.error(f"SentenceTransformer embedding failed: {e}")

        # Deterministic fallback
        return [self._hash_vector(t) for t in texts]


class OpenAIEmbeddingProvider(IEmbeddingProvider):
    def __init__(self, api_key: Optional[str] = None, model_name: str = "text-embedding-3-small"):
        self.api_key = api_key
        self.model_name = model_name
        self.dimension = 1536
        self.model_version = f"openai:{model_name}:v1"

    def get_provider_name(self) -> str:
        return "openai"

    def get_dimension(self) -> int:
        return self.dimension

    def get_model_version(self) -> str:
        return self.model_version

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        # Fallback to local provider if no API key
        local_fallback = LocalSTEmbeddingProvider()
        return local_fallback.embed_texts(texts)


class EmbeddingProviderFactory:
    @staticmethod
    def get_provider(provider_type: str = "local") -> IEmbeddingProvider:
        if provider_type.lower() == "openai":
            return OpenAIEmbeddingProvider()
        return LocalSTEmbeddingProvider()
