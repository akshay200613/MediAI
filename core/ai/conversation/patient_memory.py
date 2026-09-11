"""
Patient Episodic Memory Service (Tier 2 Semantic Memory).
Stores and recalls patient-specific consultation exchanges in Qdrant Vector DB with strict tenant isolation.
"""

from datetime import datetime, timezone
from typing import Any
import uuid

from qdrant_client.models import (
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    PayloadSchemaType,
)

from core.config.settings import settings
from core.config.logging import get_logger
from core.database.qdrant_client import get_qdrant_client, ensure_collection
from core.ai.rag.ingestion.embedder import embed_single

logger = get_logger(__name__)


class PatientMemoryService:
    """
    Manages semantic episodic memory for patients in Qdrant.
    Embeds and stores past consultation context, enabling the AI agent
    to semantically recall prior symptoms, diagnoses, and medical interactions.
    """

    def __init__(self, collection_name: str | None = None) -> None:
        self.collection_name = collection_name or f"{settings.qdrant_collection_prefix}_patient_memories"
        self._initialized = False

    async def ensure_ready(self) -> None:
        """Ensure the patient memories collection exists in Qdrant."""
        if not self._initialized:
            try:
                await ensure_collection(self.collection_name)
                # Ensure payload index for fast user_id filtering
                client = get_qdrant_client()
                try:
                    await client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name="user_id",
                        field_schema=PayloadSchemaType.KEYWORD,
                    )
                except Exception:
                    # Index may already exist
                    pass
                self._initialized = True
            except Exception as exc:
                logger.warning("Could not initialize patient memory collection", error=str(exc))

    async def index_exchange(
        self,
        user_id: str,
        patient_id: str | None,
        session_id: str,
        user_msg: str,
        assistant_msg: str,
    ) -> bool:
        """
        Extract and embed a consultation exchange into Qdrant episodic memory.
        Ignores trivial greetings and fast-path action JSON payloads.
        """
        if not user_id or not user_msg or not assistant_msg:
            return False

        clean_user = user_msg.strip()
        # Skip pure JSON payloads (e.g. fast-path booking confirmations)
        if clean_user.startswith("{") and clean_user.endswith("}"):
            return False

        # Skip trivial single-word greetings / acknowledgements
        if len(clean_user.split()) < 3 and clean_user.lower() in ("hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "bye"):
            return False

        try:
            await self.ensure_ready()

            timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            summary = (
                f"Date: {timestamp_str}\n"
                f"Patient Query: {clean_user}\n"
                f"Assistant Medical Response: {assistant_msg[:400]}"
            )

            # Generate semantic vector embedding
            embedding = await embed_single(summary)
            if not embedding:
                return False

            point_id = str(uuid.uuid4())
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "user_id": str(user_id),
                    "patient_id": str(patient_id) if patient_id else "",
                    "session_id": str(session_id),
                    "user_msg": clean_user[:500],
                    "assistant_msg": assistant_msg[:500],
                    "summary": summary,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "type": "consultation_exchange",
                },
            )

            client = get_qdrant_client()
            await client.upsert(
                collection_name=self.collection_name,
                points=[point],
            )
            logger.info("Patient episodic memory indexed", user_id=user_id, session_id=session_id)
            return True
        except Exception as exc:
            logger.warning("Failed to index patient episodic memory", user_id=user_id, error=str(exc))
            return False

    async def recall_memories(
        self,
        user_id: str,
        query: str,
        top_k: int = 3,
        score_threshold: float = 0.50,
    ) -> list[str]:
        """
        Recall semantically relevant past consultation memories strictly for this patient.
        """
        if not user_id or not query or len(query.strip()) < 3:
            return []

        clean_query = query.strip()
        if clean_query.startswith("{") and clean_query.endswith("}"):
            return []

        try:
            await self.ensure_ready()

            query_vector = await embed_single(clean_query)
            if not query_vector:
                return []

            client = get_qdrant_client()
            qdrant_filter = Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=str(user_id)),
                    )
                ]
            )

            results = await client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=top_k * 2,
                query_filter=qdrant_filter,
                with_payload=True,
            )

            memories = []
            for pt in results.points:
                if pt.score >= score_threshold and pt.payload:
                    date_prefix = pt.payload.get("created_at", "")[:10]
                    u_msg = pt.payload.get("user_msg", "")
                    a_msg = pt.payload.get("assistant_msg", "")
                    if u_msg and a_msg:
                        memories.append(f"[{date_prefix}] Patient asked: \"{u_msg}\" → Advice: \"{a_msg[:180]}...\"")

            return memories[:top_k]
        except Exception as exc:
            logger.warning("Failed to recall patient episodic memories", user_id=user_id, error=str(exc))
            return []


# Global singleton instance
_patient_memory_service: PatientMemoryService | None = None


def get_patient_memory_service() -> PatientMemoryService:
    """Get or create singleton PatientMemoryService instance."""
    global _patient_memory_service
    if _patient_memory_service is None:
        _patient_memory_service = PatientMemoryService()
    return _patient_memory_service
