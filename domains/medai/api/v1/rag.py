"""RAG Document Ingest & Query API – /api/v1/medai/rag"""
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.database.session import get_db
from core.auth.dependencies import get_current_user, CurrentUser
from core.auth.permissions import require_permission, Permission
from core.schemas.base import DataResponse
from core.ai.rag.pipeline import RAGPipeline
from core.ai.llm.litellm_client import get_llm_client
from core.config.settings import settings
from core.config.logging import get_logger

logger = get_logger("medai.rag_api")
router = APIRouter()

COLLECTION = f"{settings.qdrant_collection_prefix}_medai_knowledge"


def get_rag_pipeline() -> RAGPipeline:
    return RAGPipeline(
        llm_client=get_llm_client(),
        collection_name=COLLECTION,
        system_prompt=(
            "You are a medical knowledge assistant. Answer questions accurately "
            "using the provided medical documents. Always cite your sources."
        ),
    )


@router.post("/ingest", response_model=DataResponse[dict], status_code=201, summary="Ingest document into knowledge base")
async def ingest_document(
    file: UploadFile = File(..., description="PDF, DOCX, or TXT file"),
    title: str = Form(..., description="Document title"),
    category: str = Form("general", description="Category (e.g., clinical_guidelines, drug_info)"),
    _: CurrentUser = Depends(require_permission(Permission.MANAGE_KNOWLEDGE_BASE)),
) -> DataResponse[dict]:
    """Upload a medical document and ingest it into the RAG knowledge base."""
    # Validate file type
    allowed = {".pdf", ".docx", ".txt", ".md"}
    suffix = "." + (file.filename or "").rsplit(".", 1)[-1].lower()
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {allowed}")

    # Read file content
    content = await file.read()

    # Extract text based on file type
    text = ""
    if suffix == ".txt" or suffix == ".md":
        text = content.decode("utf-8", errors="ignore")
    elif suffix == ".pdf":
        try:
            import pypdf
            import io
            reader = pypdf.PdfReader(io.BytesIO(content))
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Failed to extract PDF text: {e}")
    elif suffix == ".docx":
        try:
            import docx
            import io
            doc = docx.Document(io.BytesIO(content))
            text = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Failed to extract DOCX text: {e}")

    if not text.strip():
        raise HTTPException(status_code=422, detail="Document appears to be empty or unreadable")

    # Ingest into RAG pipeline
    source_id = str(uuid.uuid4())
    pipeline = get_rag_pipeline()
    chunks_indexed = await pipeline.ingest(
        text=text,
        metadata={"title": title, "category": category, "filename": file.filename},
        source_id=source_id,
    )

    logger.info("Document ingested", title=title, chunks=chunks_indexed)
    return DataResponse(
        data={"source_id": source_id, "chunks_indexed": chunks_indexed, "title": title},
        message=f"Document ingested: {chunks_indexed} chunks indexed",
    )


@router.post("/query", response_model=DataResponse[dict], summary="Query the medical knowledge base")
async def query_knowledge_base(
    body: dict,
    _: CurrentUser = Depends(require_permission(Permission.USE_AI_CHAT)),
) -> DataResponse[dict]:
    """
    Directly query the RAG knowledge base without conversation history.
    Body: { "query": "...", "top_k": 5 }
    """
    query = body.get("query", "").strip()
    top_k = int(body.get("top_k", 5))

    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    pipeline = get_rag_pipeline()
    result = await pipeline.query(user_query=query, top_k=top_k)

    return DataResponse(
        data={
            "answer": result.answer,
            "sources": result.sources,
            "retrieved_chunks": result.retrieved_chunks,
            "query": result.query,
        },
        message="Query completed",
    )
