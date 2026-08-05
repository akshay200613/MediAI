"""
Medical AI Agent – specialized agent for clinic consultation and triage.
Extends BaseAgent with medical-specific system prompt and RAG pipeline.
"""

from core.ai.agents.base_agent import AgentContext, AgentResponse, BaseAgent
from core.ai.llm.client import BaseLLMClient
from core.ai.rag.pipeline import RAGPipeline
from core.config.settings import settings

MEDICAL_SYSTEM_PROMPT = """You are MedAI, an intelligent medical assistant for clinic management.

You help:
- Doctors: clinical decision support, prescription guidance, patient history summaries
- Nurses: patient triage, vital monitoring alerts, medication reminders
- Receptionists: appointment scheduling, patient registration
- Patients: symptom understanding, appointment booking, medication questions

IMPORTANT GUIDELINES:
- Always recommend consulting a qualified doctor for diagnosis
- Never prescribe medications without doctor authorization
- Flag emergency symptoms immediately (chest pain, breathing difficulty, severe bleeding)
- Maintain patient confidentiality at all times
- Be empathetic and clear in explanations

Use the provided tools and knowledge base to give accurate, evidence-based responses."""


class MedicalAgent(BaseAgent):
    """
    Specialized medical AI agent.
    Uses RAG for medical knowledge retrieval and ReAct for tool calling.
    """

    name = "medical_agent"
    description = "Intelligent medical assistant for clinic management"
    system_prompt = MEDICAL_SYSTEM_PROMPT

    def __init__(self, llm_client: BaseLLMClient) -> None:
        super().__init__(llm_client)
        self.rag = RAGPipeline(
            llm_client=llm_client,
            collection_name=f"{settings.qdrant_collection_prefix}_medai_knowledge",
            system_prompt=MEDICAL_SYSTEM_PROMPT,
        )

    async def run(self, context: AgentContext) -> AgentResponse:
        """
        Medical agent execution:
        1. Check if RAG is needed
        2. Query knowledge base if use_rag=True
        3. Generate response with medical context
        """
        use_rag = context.metadata.get("use_rag", True)
        user_message = context.messages[-1].content if context.messages else ""

        if use_rag and user_message:
            # Use RAG pipeline for grounded medical responses
            result = await self.rag.query(
                user_query=user_message,
                conversation_history=context.messages[:-1],
            )
            return AgentResponse(
                content=result.answer,
                agent_name=self.name,
                sources=result.sources,
                metadata={"retrieved_chunks": result.retrieved_chunks},
            )
        else:
            # Direct LLM response without RAG
            response = await self.llm.generate(
                context.messages,
                system_prompt=self.system_prompt,
            )
            return AgentResponse(
                content=response.content,
                agent_name=self.name,
            )
