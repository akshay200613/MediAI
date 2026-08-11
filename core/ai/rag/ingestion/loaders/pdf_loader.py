"""
PDF document loader for medical knowledge bases.
"""

from pathlib import Path

from core.ai.rag.ingestion.document import Document
from core.ai.rag.ingestion.loader import DocumentLoader


class PDFDocumentLoader(DocumentLoader):
    """Load text from PDF documents."""

    def load(self, path: Path) -> list[Document]:
        """Load a PDF and return normalized documents."""

        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise ImportError(
                "PyMuPDF is required for PDF loading. "
                "Install it with: pip install pymupdf"
            ) from exc

        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")

        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Expected a PDF file, got: {path.suffix}")

        result: list[Document] = []

        with fitz.open(path) as pdf:
            for page_number, page in enumerate(pdf, start=1):
                content = page.get_text("text").strip()

                if not content:
                    continue

                metadata = {
                    "source_file": path.name,
                    "file_type": "pdf",
                    "page_number": page_number,
                    "source_type": "medical_document",
                }

                result.append(
                    Document(
                        content=content,
                        metadata=metadata,
                    )
                )

        return result
        