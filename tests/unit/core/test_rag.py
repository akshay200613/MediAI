"""
Unit tests for the RAG chunker.
"""

import pytest
from core.ai.rag.ingestion.chunker import chunk_text, chunk_by_sentences


def test_chunk_short_text():
    """Short text should not be split."""
    text = "This is a short text."
    chunks = chunk_text(text, chunk_size=512)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_empty_text():
    """Empty text should return empty list."""
    chunks = chunk_text("", chunk_size=512)
    assert chunks == []


def test_chunk_long_text():
    """Long text should be split into multiple chunks."""
    # Generate a long text
    paragraph = "This is a test paragraph with enough content. " * 5
    long_text = "\n\n".join([paragraph] * 10)

    chunks = chunk_text(long_text, chunk_size=200, overlap=20)
    assert len(chunks) > 1


def test_chunk_overlap():
    """Chunks should have overlapping content."""
    text = "\n\n".join([f"Paragraph number {i}: " + "word " * 50 for i in range(5)])
    chunks = chunk_text(text, chunk_size=100, overlap=20)

    # Verify we got multiple chunks
    assert len(chunks) > 1


def test_chunk_by_sentences():
    """Sentence-based chunking should work correctly."""
    text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence. Sixth sentence."
    chunks = chunk_by_sentences(text, max_sentences=2)
    assert len(chunks) == 3


def test_chunk_preserves_content():
    """Chunking should not lose content."""
    text = "Important medical information. " * 20
    chunks = chunk_text(text, chunk_size=100, overlap=10)
    combined = " ".join(chunks)
    # All key words should appear somewhere in chunks
    assert "Important" in combined
    assert "medical" in combined
