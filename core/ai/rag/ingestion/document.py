"""
Core document models used throughout the RAG ingestion pipeline.

The same Document/DocumentChunk models are shared by:
    Document loaders
        ↓
    Chunking
        ↓
    Dense index (Qdrant)
    Sparse index (BM25)
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Document:
    """
    Normalized source document.

    A Document represents the original logical source before
    chunking. It is independent of the original file format.
    """

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate and normalize the document."""

        self.content = self.content.strip()

        if not self.content:
            raise ValueError("Document content cannot be empty.")


@dataclass(slots=True)
class DocumentChunk:
    """
    A searchable chunk derived from a Document.

    This object is shared by both dense and sparse retrieval:

        DocumentChunk
             ├──→ Gemini embedding → Qdrant
             │
             └──→ BM25 index
    """

    chunk_id: str
    document_id: str
    text: str
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate and normalize the chunk."""

        self.text = self.text.strip()

        if not self.text:
            raise ValueError("Document chunk text cannot be empty.")

        if self.chunk_index < 0:
            raise ValueError("chunk_index cannot be negative.")

    def to_payload(self) -> dict[str, Any]:
        """
        Convert the chunk into a Qdrant payload.

        Returns:
            Dictionary suitable for Qdrant point payload.
        """

        return {
            "text": self.text,
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            **self.metadata,
        }