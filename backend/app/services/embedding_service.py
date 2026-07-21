"""
Embedding generation and vector index management.

Architecture decision — FAISS over a hosted vector DB (Qdrant/Pinecone):
at the scale of a single researcher's personal library (hundreds to a
few thousand papers, tens of thousands of chunks), an in-process FAISS
IndexFlatIP per user is faster to query, has zero network hop, costs
nothing to run, and is trivial to delete (rm the file) on account
deletion for GDPR-style compliance. The `VectorIndexStore` abstraction
below is the seam: swapping to Qdrant for a future multi-tenant/
shared-corpus feature means implementing this same interface against
Qdrant's client, nothing above this layer changes (see docs/adr/ADR-002).

Embedder abstraction — the app depends on `Embedder`, an interface, not
a concrete model. Production uses `SentenceTransformerEmbedder`
(all-MiniLM-L6-v2: 384-dim, runs on CPU, no external API call, so
embedding — unlike generation — works fully offline). Tests inject
`DeterministicHashEmbedder`, a zero-dependency stand-in that produces
stable, distinct vectors for distinct strings, so unit tests don't need
model weights or network access.
"""
from __future__ import annotations

import hashlib
import os
import threading
from abc import ABC, abstractmethod

import faiss
import numpy as np

from app.core.config import get_settings

settings = get_settings()


class Embedder(ABC):
    dim: int

    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:
        """Return an (N, dim) float32, L2-normalized matrix."""
        raise NotImplementedError


class SentenceTransformerEmbedder(Embedder):
    """Production embedder. Loaded lazily so app startup doesn't pay the
    model-load cost when no embedding work is happening yet, and so the
    rest of the app can boot even if model weights aren't cached yet."""

    _model = None
    _lock = threading.Lock()

    def __init__(self, model_name: str = settings.EMBEDDING_MODEL_NAME, dim: int = settings.EMBEDDING_DIM):
        self.model_name = model_name
        self.dim = dim

    def _get_model(self):
        if SentenceTransformerEmbedder._model is None:
            with SentenceTransformerEmbedder._lock:
                if SentenceTransformerEmbedder._model is None:
                    from sentence_transformers import SentenceTransformer

                    SentenceTransformerEmbedder._model = SentenceTransformer(self.model_name)
        return SentenceTransformerEmbedder._model

    def embed(self, texts: list[str]) -> np.ndarray:
        model = self._get_model()
        vectors = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return vectors.astype("float32")


class DeterministicHashEmbedder(Embedder):
    """Test/offline-fallback embedder: deterministic, dependency-free.

    Not used in production RAG — it has no real semantic meaning, only
    stable hashing so identical/similar strings land near each other in
    tests without downloading a model. Kept honest and documented rather
    than silently substituted.
    """

    def __init__(self, dim: int = 384):
        self.dim = dim

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.dim), dtype="float32")
        for i, text in enumerate(texts):
            for token_idx, token in enumerate(text.lower().split()):
                h = int(hashlib.sha256(token.encode()).hexdigest(), 16)
                vectors[i, h % self.dim] += 1.0
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms


class VectorIndexStore:
    """Owns one FAISS IndexFlatIP file per user on disk."""

    def __init__(self, index_dir: str = settings.VECTOR_INDEX_DIR, dim: int = settings.EMBEDDING_DIM):
        self.index_dir = index_dir
        self.dim = dim
        os.makedirs(self.index_dir, exist_ok=True)
        self._locks: dict[int, threading.Lock] = {}

    def _path(self, user_id: int) -> str:
        return os.path.join(self.index_dir, f"user_{user_id}.index")

    def _lock_for(self, user_id: int) -> threading.Lock:
        self._locks.setdefault(user_id, threading.Lock())
        return self._locks[user_id]

    def _load_or_create(self, user_id: int) -> faiss.Index:
        path = self._path(user_id)
        if os.path.exists(path):
            return faiss.read_index(path)
        return faiss.IndexFlatIP(self.dim)

    def add(self, user_id: int, vectors: np.ndarray) -> int:
        """Append vectors, return the starting row offset assigned to them."""
        with self._lock_for(user_id):
            index = self._load_or_create(user_id)
            start_row = index.ntotal
            index.add(vectors)
            faiss.write_index(index, self._path(user_id))
            return start_row

    def search(self, user_id: int, query_vector: np.ndarray, top_k: int) -> tuple[list[int], list[float]]:
        """Return (row_ids, scores) for the top_k nearest vectors."""
        path = self._path(user_id)
        if not os.path.exists(path):
            return [], []
        with self._lock_for(user_id):
            index = faiss.read_index(path)
        if index.ntotal == 0:
            return [], []
        scores, ids = index.search(query_vector.reshape(1, -1), min(top_k, index.ntotal))
        return ids[0].tolist(), scores[0].tolist()

    def delete_user_index(self, user_id: int) -> None:
        path = self._path(user_id)
        if os.path.exists(path):
            os.remove(path)
