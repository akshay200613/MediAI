"""
Generic document loading interface.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from core.ai.rag.ingestion.document import Document


class DocumentLoader(ABC):
    """Base interface for all document loaders."""

    @abstractmethod
    def load(self, path: Path) -> list[Document]:
        """Load a file and return normalized documents."""
        raise NotImplementedError