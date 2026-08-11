"""
Generic knowledge-base ingestion.

Scans the knowledge-base directory recursively, loads supported files,
normalizes them into Documents, chunks them, and indexes the chunks
through the RAG pipeline.

Indexing:

    Document
        ↓
    DocumentChunk[]
        ├──→ Qdrant dense index
        └──→ BM25 sparse index

Usage:

    python -m core.ai.rag.ingestion.ingest
"""

from __future__ import annotations

from pathlib import Path

from core.ai.llm.gemini_client import get_llm_client
from core.ai.rag.ingestion.loaders.json_loader import JSONDocumentLoader
from core.ai.rag.ingestion.loaders.pdf_loader import PDFDocumentLoader
from core.ai.rag.pipeline import RAGPipeline
from core.config.logging import get_logger
from core.config.settings import settings


logger = get_logger(__name__)


# ============================================================================
# Paths
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

KNOWLEDGE_BASE_DIR = (
    PROJECT_ROOT
    / "data"
    / "knowledge_base"
)


# ============================================================================
# Loader registry
# ============================================================================

LOADERS = {
    ".json": JSONDocumentLoader,
    ".pdf": PDFDocumentLoader,
}


def get_loader(file_path: Path):
    """
    Return the appropriate loader for a file.

    Args:
        file_path: Path to the source document.

    Returns:
        Loader instance.

    Raises:
        ValueError: If the file format is unsupported.
    """

    extension = file_path.suffix.lower()

    loader_class = LOADERS.get(extension)

    if loader_class is None:
        raise ValueError(
            f"Unsupported file format: {extension}"
        )

    return loader_class()


# ============================================================================
# File discovery
# ============================================================================

def discover_files() -> list[Path]:
    """
    Recursively discover files in the knowledge base.
    """

    if not KNOWLEDGE_BASE_DIR.exists():
        raise FileNotFoundError(
            f"Knowledge base directory does not exist: "
            f"{KNOWLEDGE_BASE_DIR}"
        )

    return sorted(
        path
        for path in KNOWLEDGE_BASE_DIR.rglob("*")
        if path.is_file()
    )


# ============================================================================
# Knowledge-base ingestion
# ============================================================================

async def ingest_knowledge_base() -> None:
    """
    Ingest all supported knowledge-base files.

    Pipeline:

        Files
          ↓
        Loader
          ↓
        Documents
          ↓
        DocumentChunks
          ├──→ Qdrant
          └──→ BM25
    """

    logger.info(
        "Starting knowledge base ingestion",
        directory=str(KNOWLEDGE_BASE_DIR),
    )

    # ------------------------------------------------------------------------
    # Discover files
    # ------------------------------------------------------------------------

    files = discover_files()

    if not files:
        logger.warning(
            "No files found in knowledge base",
            directory=str(KNOWLEDGE_BASE_DIR),
        )
        return

    logger.info(
        "Files discovered",
        count=len(files),
    )

    # ------------------------------------------------------------------------
    # Create RAG pipeline
    # ------------------------------------------------------------------------

    llm_client = get_llm_client()

    collection_name = (
        f"{settings.qdrant_collection_prefix}_knowledge"
    )

    rag = RAGPipeline(
        llm_client=llm_client,
        collection_name=collection_name,
    )

    # ------------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------------

    total_files = 0
    total_documents = 0
    total_chunks = 0
    total_skipped = 0

    # ------------------------------------------------------------------------
    # Process files
    # ------------------------------------------------------------------------

    for file_path in files:

        try:
            logger.info(
                "Processing file",
                file=str(file_path),
            )

            # ---------------------------------------------------------------
            # Select loader
            # ---------------------------------------------------------------

            loader = get_loader(file_path)

            # ---------------------------------------------------------------
            # Load file → Documents
            # ---------------------------------------------------------------

            documents = loader.load(file_path)

            if not documents:
                logger.warning(
                    "No documents extracted from file",
                    file=str(file_path),
                )

                total_skipped += 1
                continue

            # ---------------------------------------------------------------
            # Add common ingestion metadata
            # ---------------------------------------------------------------

            relative_path = file_path.relative_to(
                KNOWLEDGE_BASE_DIR
            )

            for document in documents:
                document.metadata.update(
                    {
                        "knowledge_base_path": str(
                            relative_path
                        ),
                        "source_file": file_path.name,
                        "source_type": file_path.suffix.lower().lstrip("."),
                    }
                )

            # ---------------------------------------------------------------
            # Document → chunks → Qdrant + BM25
            # ---------------------------------------------------------------

            chunk_count, _ = await rag.ingest_documents(
                documents
            )

            total_files += 1
            total_documents += len(documents)
            total_chunks += chunk_count

            logger.info(
                "File ingested successfully",
                file=str(file_path),
                documents=len(documents),
                chunks=chunk_count,
            )

        except ValueError as exc:

            total_skipped += 1

            logger.warning(
                "Skipping unsupported file",
                file=str(file_path),
                error=str(exc),
            )

        except Exception as exc:

            total_skipped += 1

            logger.error(
                "Failed to ingest file",
                file=str(file_path),
                error=str(exc),
            )

    # ------------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------------

    logger.info(
        "Knowledge base ingestion completed",
        files=total_files,
        documents=total_documents,
        chunks=total_chunks,
        skipped=total_skipped,
        qdrant_collection=collection_name,
    )


# ============================================================================
# CLI entry point
# ============================================================================

if __name__ == "__main__":
    import asyncio

    asyncio.run(
        ingest_knowledge_base()
    )
    