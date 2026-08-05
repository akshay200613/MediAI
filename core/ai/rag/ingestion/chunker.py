"""
Text chunker – splits documents into overlapping chunks for RAG ingestion.
"""

import re
from typing import Iterator


def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 64,
    separator: str = "\n\n",
) -> list[str]:
    """
    Split text into overlapping chunks.

    Strategy:
    1. Try to split on paragraph boundaries (double newlines)
    2. Fall back to sentence boundaries
    3. Fall back to character-level splitting

    Args:
        text: Input text to chunk
        chunk_size: Target number of characters per chunk
        overlap: Number of characters to overlap between chunks
        separator: Primary split separator

    Returns:
        List of text chunks
    """
    # Clean whitespace
    text = re.sub(r"\n{3,}", "\n\n", text.strip())

    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    # Try paragraph-based splitting first
    paragraphs = text.split(separator)
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk = f"{current_chunk}\n\n{para}".strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
                # Add overlap from end of current chunk
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = f"{overlap_text}\n\n{para}".strip()
            else:
                # Paragraph itself is too large, split by sentences
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return [c for c in chunks if len(c.strip()) > 10]


def chunk_by_sentences(text: str, max_sentences: int = 5) -> list[str]:
    """Split text into chunks of N sentences each."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    for i in range(0, len(sentences), max_sentences):
        chunk = " ".join(sentences[i:i + max_sentences])
        if chunk.strip():
            chunks.append(chunk)
    return chunks
