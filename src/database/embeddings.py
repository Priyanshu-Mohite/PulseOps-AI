"""
Local, 0-cost Vector Embeddings Generator using FastEmbed (BAAI/bge-small-en-v1.5).
Generates 384-dimensional dense vectors on CPU with ultra-low latency.
"""

from typing import List
from fastembed import TextEmbedding

# Model name: BAAI/bge-small-en-v1.5 produces 384-dim normalized vectors
MODEL_NAME = "BAAI/bge-small-en-v1.5"

_embedding_model = None


def get_embedding_model() -> TextEmbedding:
    """Singleton getter for the FastEmbed TextEmbedding model."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = TextEmbedding(model_name=MODEL_NAME)
    return _embedding_model


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate 384-dimensional vector embeddings for a list of texts.
    Returns list of standard Python floats suitable for psycopg2 / pgvector.
    """
    if not texts:
        return []

    model = get_embedding_model()
    embeddings_generator = model.embed(texts)
    # Convert numpy.float32 to standard Python float for psycopg2 adapter
    return [[float(x) for x in emb] for emb in embeddings_generator]


def generate_single_embedding(text: str) -> List[float]:
    """Generate vector embedding for a single text query."""
    embeddings = generate_embeddings([text])
    return embeddings[0] if embeddings else []


if __name__ == "__main__":
    test_text = "Project Phoenix Kafka Ingestion pipeline setup"
    emb = generate_single_embedding(test_text)
    print(f"Generated embedding dimensions: {len(emb)}")
    print(f"Sample values (Python floats): {emb[:5]}")
    print(f"Type of elements: {type(emb[0])}")
