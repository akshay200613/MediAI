"""
Integration tests for the RAG API endpoints.

Tests POST /api/v1/medai/rag/ingest and POST /api/v1/medai/rag/query.
All Qdrant / LLM calls are mocked.
"""

import uuid
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

RAG_BASE = "/api/v1/medai/rag"


# ─── POST /rag/ingest ─────────────────────────────────────────────────────────

class TestIngestEndpoint:
    async def test_ingest_requires_auth(self, async_client: AsyncClient):
        resp = await async_client.post(
            f"{RAG_BASE}/ingest",
            files={"file": ("doc.txt", BytesIO(b"text"), "text/plain")},
            data={"title": "Test"},
        )
        assert resp.status_code in (401, 403)

    async def test_patient_cannot_ingest(
        self, async_client: AsyncClient, patient_headers: dict
    ):
        resp = await async_client.post(
            f"{RAG_BASE}/ingest",
            headers=patient_headers,
            files={"file": ("doc.txt", BytesIO(b"text"), "text/plain")},
            data={"title": "Test"},
        )
        assert resp.status_code == 403

    async def test_doctor_cannot_ingest(
        self, async_client: AsyncClient, doctor_headers: dict
    ):
        resp = await async_client.post(
            f"{RAG_BASE}/ingest",
            headers=doctor_headers,
            files={"file": ("doc.txt", BytesIO(b"text"), "text/plain")},
            data={"title": "Test"},
        )
        assert resp.status_code == 403

    async def test_admin_ingest_txt_success(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        content = b"Hypertension is a chronic condition affecting blood pressure."
        with patch("domains.medai.api.v1.rag.RAGPipeline") as MockRAG:
            mock_pipeline = MagicMock()
            mock_pipeline.ingest = AsyncMock(return_value=3)
            MockRAG.return_value = mock_pipeline

            resp = await async_client.post(
                f"{RAG_BASE}/ingest",
                headers=admin_headers,
                files={"file": ("guideline.txt", BytesIO(content), "text/plain")},
                data={"title": "Hypertension Guide", "category": "clinical_guidelines"},
            )

        assert resp.status_code == 201
        body = resp.json()
        assert body["success"] is True
        assert "source_id" in body["data"]
        assert body["data"]["chunks_indexed"] == 3
        assert body["data"]["title"] == "Hypertension Guide"

    async def test_admin_ingest_md_file(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        content = b"# Drug Reference\n\nAspirin is used for pain relief."
        with patch("domains.medai.api.v1.rag.RAGPipeline") as MockRAG:
            mock_pipeline = MagicMock()
            mock_pipeline.ingest = AsyncMock(return_value=2)
            MockRAG.return_value = mock_pipeline

            resp = await async_client.post(
                f"{RAG_BASE}/ingest",
                headers=admin_headers,
                files={"file": ("drugs.md", BytesIO(content), "text/markdown")},
                data={"title": "Drug Reference", "category": "drug_info"},
            )

        assert resp.status_code == 201

    async def test_unsupported_file_type_returns_400(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        resp = await async_client.post(
            f"{RAG_BASE}/ingest",
            headers=admin_headers,
            files={"file": ("virus.exe", BytesIO(b"\x00\x01\x02"), "application/octet-stream")},
            data={"title": "Bad File"},
        )
        assert resp.status_code == 400
        assert "unsupported" in resp.json()["detail"].lower()

    async def test_empty_txt_file_returns_422(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """An uploaded file with no extractable text → 422."""
        with patch("domains.medai.api.v1.rag.RAGPipeline") as MockRAG:
            MockRAG.return_value = MagicMock()

            resp = await async_client.post(
                f"{RAG_BASE}/ingest",
                headers=admin_headers,
                files={"file": ("empty.txt", BytesIO(b"   \n\n  "), "text/plain")},
                data={"title": "Empty"},
            )

        assert resp.status_code == 422

    async def test_ingest_returns_source_id(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        with patch("domains.medai.api.v1.rag.RAGPipeline") as MockRAG:
            mock_pipeline = MagicMock()
            mock_pipeline.ingest = AsyncMock(return_value=4)
            MockRAG.return_value = mock_pipeline

            resp = await async_client.post(
                f"{RAG_BASE}/ingest",
                headers=admin_headers,
                files={"file": ("data.txt", BytesIO(b"Medical knowledge base content."), "text/plain")},
                data={"title": "Knowledge Base"},
            )

        body = resp.json()
        source_id = body["data"]["source_id"]
        # Must be a valid UUID
        uuid.UUID(source_id)


# ─── POST /rag/query ─────────────────────────────────────────────────────────

class TestQueryEndpoint:
    def _mock_rag_result(self, answer: str = "Based on the knowledge base...") -> MagicMock:
        result = MagicMock()
        result.answer = answer
        result.sources = [{"title": "Clinical Guide", "score": 0.92}]
        result.retrieved_chunks = 3
        result.query = "test query"
        return result

    async def test_query_requires_auth(self, async_client: AsyncClient):
        resp = await async_client.post(
            f"{RAG_BASE}/query", json={"query": "what is diabetes"}
        )
        assert resp.status_code in (401, 403)

    async def test_patient_can_query(
        self, async_client: AsyncClient, patient_headers: dict
    ):
        with patch("domains.medai.api.v1.rag.RAGPipeline") as MockRAG:
            mock_pipeline = MagicMock()
            mock_pipeline.query = AsyncMock(return_value=self._mock_rag_result())
            MockRAG.return_value = mock_pipeline

            resp = await async_client.post(
                f"{RAG_BASE}/query",
                json={"query": "what is diabetes", "top_k": 3},
                headers=patient_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "answer" in body["data"]
        assert "sources" in body["data"]

    async def test_doctor_can_query(
        self, async_client: AsyncClient, doctor_headers: dict
    ):
        with patch("domains.medai.api.v1.rag.RAGPipeline") as MockRAG:
            mock_pipeline = MagicMock()
            mock_pipeline.query = AsyncMock(
                return_value=self._mock_rag_result("Hypertension is managed with...")
            )
            MockRAG.return_value = mock_pipeline

            resp = await async_client.post(
                f"{RAG_BASE}/query",
                json={"query": "hypertension management"},
                headers=doctor_headers,
            )

        assert resp.status_code == 200

    async def test_admin_can_query(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        with patch("domains.medai.api.v1.rag.RAGPipeline") as MockRAG:
            mock_pipeline = MagicMock()
            mock_pipeline.query = AsyncMock(return_value=self._mock_rag_result())
            MockRAG.return_value = mock_pipeline

            resp = await async_client.post(
                f"{RAG_BASE}/query",
                json={"query": "clinical guidelines for fever"},
                headers=admin_headers,
            )

        assert resp.status_code == 200

    async def test_empty_query_returns_400(
        self, async_client: AsyncClient, patient_headers: dict
    ):
        resp = await async_client.post(
            f"{RAG_BASE}/query",
            json={"query": ""},
            headers=patient_headers,
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    async def test_query_whitespace_only_returns_400(
        self, async_client: AsyncClient, patient_headers: dict
    ):
        resp = await async_client.post(
            f"{RAG_BASE}/query",
            json={"query": "   "},
            headers=patient_headers,
        )
        assert resp.status_code == 400

    async def test_query_response_contains_all_fields(
        self, async_client: AsyncClient, doctor_headers: dict
    ):
        result = self._mock_rag_result("Detailed answer here.")
        with patch("domains.medai.api.v1.rag.RAGPipeline") as MockRAG:
            mock_pipeline = MagicMock()
            mock_pipeline.query = AsyncMock(return_value=result)
            MockRAG.return_value = mock_pipeline

            resp = await async_client.post(
                f"{RAG_BASE}/query",
                json={"query": "medication dosage"},
                headers=doctor_headers,
            )

        data = resp.json()["data"]
        assert "answer" in data
        assert "sources" in data
        assert "retrieved_chunks" in data
        assert "query" in data

    async def test_query_top_k_parameter_accepted(
        self, async_client: AsyncClient, doctor_headers: dict
    ):
        with patch("domains.medai.api.v1.rag.RAGPipeline") as MockRAG:
            mock_pipeline = MagicMock()
            mock_pipeline.query = AsyncMock(return_value=self._mock_rag_result())
            MockRAG.return_value = mock_pipeline

            resp = await async_client.post(
                f"{RAG_BASE}/query",
                json={"query": "pain management", "top_k": 10},
                headers=doctor_headers,
            )

        assert resp.status_code == 200
