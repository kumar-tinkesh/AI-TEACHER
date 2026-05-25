import logging
from typing import List, Optional
import numpy as np

logger = logging.getLogger("embeddings")

# Eager-loaded model instance
_model = None


def load_model():
    """Load the sentence-transformer model on startup."""
    global _model
    if _model is None:
        logger.info("Loading embedding model...")
        from sentence_transformers import SentenceTransformer
        try:
            # Try local cache first (fast, no network requests)
            _model = SentenceTransformer(
                "sentence-transformers/all-MiniLM-L6-v2",
                local_files_only=True,
            )
            logger.info("Embedding model loaded from local cache.")
        except Exception:
            # Fallback: download from HuggingFace (first run only)
            logger.info("Model not cached locally, downloading from HuggingFace...")
            _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            logger.info("Embedding model downloaded and loaded.")


def _get_model():
    """Return the pre-loaded model."""
    if _model is None:
        raise RuntimeError("Embedding model not loaded. Call load_model() on startup.")
    return _model


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of texts into dense vectors.
    Returns a list of float vectors.
    """
    if not texts:
        return []
    model = _get_model()
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return embeddings.tolist()


def embed_query(text: str) -> List[float]:
    """Embed a single query string."""
    return embed_texts([text])[0]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a_vec = np.array(a, dtype=np.float32)
    b_vec = np.array(b, dtype=np.float32)
    norm = np.linalg.norm(a_vec) * np.linalg.norm(b_vec)
    if norm == 0:
        return 0.0
    return float(np.dot(a_vec, b_vec) / norm)


def rank_chunks_by_similarity(query_embedding: List[float], chunks: List[dict]) -> List[dict]:
    """
    Rank chunks by cosine similarity to query embedding.
    Adds a 'score' field to each chunk dict.
    Chunks without embeddings get score 0.0.
    """
    scored = []
    for chunk in chunks:
        emb = chunk.get("embedding")
        score = cosine_similarity(query_embedding, emb) if emb else 0.0
        scored.append({**chunk, "score": round(score, 4)})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored
