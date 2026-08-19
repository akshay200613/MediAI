"""
Embedder – generates vector embeddings using Gemini.
"""

from core.config.logging import get_logger

logger = get_logger(__name__)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a batch of texts using Gemini.
    Returns a list of embedding vectors.
    """
    from core.ai.llm.litellm_client import get_llm_client
    client = get_llm_client()

    embeddings = []
    for text in texts:
        embedding = await client.embed(
            text,
            task_type="RETRIEVAL_DOCUMENT",
        )
        embeddings.append(embedding)

    logger.debug("Embeddings generated", count=len(texts))
    return embeddings


async def embed_single(text: str) -> list[float]:
    """Generate an embedding for a single text."""
    results = await embed_texts([text])
    return results[0]
