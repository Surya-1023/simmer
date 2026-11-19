from functools import lru_cache
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 32


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """Load the embedding model once per backend process."""
    return SentenceTransformer(MODEL_NAME)


def warm_up_embedding_model() -> None:
    """Load the model and run one small encode before the first user request."""
    get_embedding_model().encode(
        ["recipe ingredient search warmup"],
        normalize_embeddings=True,
        show_progress_bar=False,
    )


@lru_cache(maxsize=512)
def _cached_embedding(text: str) -> tuple[float, ...]:
    vector = get_embedding_model().encode(
        text,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return tuple(float(value) for value in vector.tolist())


def generate_embedding(text: str) -> list[float]:
    """Create a normalized query vector; repeated queries use a small LRU cache."""
    normalized_text = " ".join(text.casefold().split())
    return list(_cached_embedding(normalized_text))


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Batch-encode recipe documents for faster ingestion."""
    if not texts:
        return []

    vectors = get_embedding_model().encode(
        texts,
        batch_size=BATCH_SIZE,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return vectors.tolist()
