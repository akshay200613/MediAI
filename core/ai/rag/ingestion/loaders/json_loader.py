"""
JSON document loader for structured knowledge bases.
"""

import json
from pathlib import Path
from typing import Any

from core.ai.rag.ingestion.document import Document
from core.ai.rag.ingestion.loader import DocumentLoader


class JSONDocumentLoader(DocumentLoader):
    """Load structured JSON knowledge bases."""

    def load(self, path: Path) -> list[Document]:
        """Load documents from a JSON knowledge base."""

        with path.open("r", encoding="utf-8") as file:
            data: dict[str, Any] = json.load(file)

        documents = data.get("documents", [])

        if not isinstance(documents, list):
            raise ValueError(
                f"Expected 'documents' to be a list in {path}"
            )

        result: list[Document] = []

        for item in documents:
            content = item.get("content")

            if not isinstance(content, str) or not content.strip():
                continue

            metadata = {
                "document_id": item.get("id"),
                "category": item.get("category"),
                "source_url": item.get("source_url"),
                "source_file": path.name,
                "file_type": "json",
                "hospital_name": data.get("hospital_name"),
                "last_updated": data.get("last_updated"),
                "source_type": "hospital_knowledge",
            }

            result.append(
                Document(
                    content=content.strip(),
                    metadata=metadata,
                )
            )

        return result
        