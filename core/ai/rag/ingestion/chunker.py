"""
Document chunking for the MedAI RAG pipeline.

Converts a normalized Document into DocumentChunk objects that can
be shared by all retrieval indexes.

Flow:

    Document
       ↓
    Chunker
       ↓
    DocumentChunk[]
       ├──→ Qdrant
       └──→ BM25
"""

from __future__ import annotations

import re
from uuid import NAMESPACE_URL, uuid5

from core.ai.rag.ingestion.document import Document, DocumentChunk


def chunk_document(
    document: Document,
    *,
    chunk_size: int = 512,
    overlap: int = 64,
    separator: str = "\n\n",
) -> list[DocumentChunk]:
    """
    Split a Document into searchable DocumentChunk objects.

    Args:
        document: Source document.
        chunk_size: Target maximum chunk size in characters.
        overlap: Number of characters shared between chunks.
        separator: Primary paragraph separator.

    Returns:
        List of DocumentChunk objects.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if overlap < 0:
        raise ValueError("overlap cannot be negative.")

    if overlap >= chunk_size:
        raise ValueError(
            "overlap must be smaller than chunk_size."
        )

    text = _clean_text(document.content)

    if not text:
        return []

    raw_chunks = _split_text(
        text=text,
        chunk_size=chunk_size,
        overlap=overlap,
        separator=separator,
    )

    document_id = _get_document_id(document)

    return [
        DocumentChunk(
            chunk_id=_create_chunk_id(
                document_id=document_id,
                chunk_index=index,
            ),
            document_id=document_id,
            text=chunk,
            chunk_index=index,
            metadata=document.metadata.copy(),
        )
        for index, chunk in enumerate(raw_chunks)
    ]


def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 64,
    separator: str = "\n\n",
) -> list[str]:
    """
    Backward-compatible text chunking function.

    This preserves the API used by existing code.

    For the hybrid RAG pipeline, prefer `chunk_document()`.
    """

    if not text or not text.strip():
        return []

    temporary_document = Document(content=text)

    chunks = chunk_document(
        temporary_document,
        chunk_size=chunk_size,
        overlap=overlap,
        separator=separator,
    )

    return [chunk.text for chunk in chunks]


def chunk_by_sentences(
    text: str,
    max_sentences: int = 5,
) -> list[str]:
    """
    Split text into groups containing up to N sentences.
    """

    if max_sentences <= 0:
        raise ValueError(
            "max_sentences must be greater than zero."
        )

    text = _clean_text(text)

    if not text:
        return []

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text,
    )

    return [
        " ".join(sentences[index:index + max_sentences]).strip()
        for index in range(
            0,
            len(sentences),
            max_sentences,
        )
        if " ".join(
            sentences[index:index + max_sentences]
        ).strip()
    ]


def _clean_text(text: str) -> str:
    """Normalize excessive whitespace."""

    return re.sub(
        r"\n{3,}",
        "\n\n",
        text.strip(),
    )


def _split_text(
    *,
    text: str,
    chunk_size: int,
    overlap: int,
    separator: str,
) -> list[str]:
    """
    Perform paragraph-first chunking with sentence fallback.
    """

    if len(text) <= chunk_size:
        return [text]

    paragraphs = [
        paragraph.strip()
        for paragraph in text.split(separator)
        if paragraph.strip()
    ]

    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        candidate = (
            f"{current}\n\n{paragraph}".strip()
            if current
            else paragraph
        )

        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)

        # If a paragraph itself is too large,
        # split it into smaller pieces.
        if len(paragraph) > chunk_size:
            paragraph_chunks = _split_large_text(
                paragraph,
                chunk_size=chunk_size,
                overlap=overlap,
            )

            chunks.extend(paragraph_chunks[:-1])

            current = paragraph_chunks[-1]

        else:
            overlap_text = _get_overlap(
                current,
                overlap,
            )

            current = (
                f"{overlap_text}\n\n{paragraph}".strip()
                if overlap_text
                else paragraph
            )

    if current:
        chunks.append(current)

    return [
        chunk
        for chunk in chunks
        if len(chunk.strip()) > 10
    ]


def _split_large_text(
    text: str,
    *,
    chunk_size: int,
    overlap: int,
) -> list[str]:
    """
    Split oversized text using sentence boundaries first,
    then character boundaries.
    """

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text,
    )

    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()

        if not sentence:
            continue

        candidate = (
            f"{current} {sentence}".strip()
            if current
            else sentence
        )

        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)

        if len(sentence) > chunk_size:
            character_chunks = _split_by_characters(
                sentence,
                chunk_size=chunk_size,
                overlap=overlap,
            )

            chunks.extend(character_chunks[:-1])
            current = character_chunks[-1]
        else:
            overlap_text = _get_overlap(
                current,
                overlap,
            )

            current = (
                f"{overlap_text} {sentence}".strip()
                if overlap_text
                else sentence
            )

    if current:
        chunks.append(current)

    return chunks


def _split_by_characters(
    text: str,
    *,
    chunk_size: int,
    overlap: int,
) -> list[str]:
    """Final fallback for text that cannot be split semantically."""

    chunks: list[str] = []

    start = 0

    while start < len(text):
        end = min(
            start + chunk_size,
            len(text),
        )

        chunks.append(
            text[start:end].strip()
        )

        if end >= len(text):
            break

        start = end - overlap

    return [
        chunk
        for chunk in chunks
        if chunk
    ]


def _get_overlap(
    text: str,
    overlap: int,
) -> str:
    """Return the trailing overlap portion of a chunk."""

    if overlap <= 0 or not text:
        return ""

    return text[-overlap:].strip()


def _get_document_id(
    document: Document,
) -> str:
    """
    Resolve a stable document ID.

    Prefer an existing metadata ID. Otherwise derive one
    deterministically from the document metadata/content.
    """

    metadata_id = (
        document.metadata.get("document_id")
        or document.metadata.get("source_id")
    )

    if metadata_id:
        return str(metadata_id)

    source = (
        document.metadata.get("source_file")
        or document.metadata.get("knowledge_base_path")
        or document.content[:200]
    )

    return str(
        uuid5(
            NAMESPACE_URL,
            str(source),
        )
    )


def _create_chunk_id(
    *,
    document_id: str,
    chunk_index: int,
) -> str:
    """Create a deterministic unique chunk ID."""

    return str(
        uuid5(
            NAMESPACE_URL,
            f"{document_id}:{chunk_index}",
        )
    )
    