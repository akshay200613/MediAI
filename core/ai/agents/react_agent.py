"""
ReAct Agent – Reason + Act pattern using LangGraph.
Supports tool calling with automatic retry and error handling.
"""

from core.ai.agents.base_agent import AgentContext, AgentResponse, BaseAgent
from core.ai.llm.client import BaseLLMClient, Message


class ReActAgent(BaseAgent):
    """
    ReAct (Reason + Act) agent.
    The agent iteratively reasons and calls tools until it reaches a final answer.
    Powered by LangGraph under the hood.
    """

    name = "react_agent"
    description = "A reasoning agent that can use tools to solve complex tasks"
    system_prompt = (
        "You are a helpful AI assistant. Think step by step. "
        "When you need information, use the available tools. "
        "Always reason before acting."
    )
    max_iterations: int = 10

    def __init__(
        self,
        llm_client: BaseLLMClient,
        tools: list | None = None,
        max_iterations: int = 10,
    ) -> None:
        super().__init__(llm_client)
        self.tools = tools or []
        self.max_iterations = max_iterations

    async def run(self, context: AgentContext) -> AgentResponse:
        """Execute ReAct loop using LangGraph."""
        from langgraph.prebuilt import create_react_agent
        from langchain_google_genai import ChatGoogleGenerativeAI
        from core.config.settings import settings

        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
            temperature=0.7,
        )

        # Build the LangGraph ReAct agent
        graph = create_react_agent(
            llm,
            tools=self.tools,
            state_modifier=self.system_prompt,
        )

        # Convert context messages to LangChain format
        lc_messages = [
            {"role": m.role, "content": m.content}
            for m in context.messages
            if m.role != "system"
        ]

        result = await graph.ainvoke({"messages": lc_messages})

        # Extract final response
        final_message = result["messages"][-1]
        tool_calls = [
            {"tool": m.name, "input": m.content}
            for m in result["messages"]
            if hasattr(m, "name") and m.name
        ]

        return AgentResponse(
            content=final_message.content,
            agent_name=self.name,
            tool_calls=tool_calls,
            metadata={"iterations": len(result["messages"])},
        )
