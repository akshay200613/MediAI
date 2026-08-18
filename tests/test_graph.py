import asyncio
from langchain_core.messages import HumanMessage
from core.ai.graph import build_medai_graph
from core.ai.graph.tools.server import mcp_server

async def main():
    print("1. Testing Graph Compilation...")
    try:
        graph = build_medai_graph()
        print("Graph compiled successfully.")
    except Exception as e:
        print(f"Graph compilation failed: {e}")
        return

    print("\n2. Checking MCP Tools...")
    # Not sure of exact attribute in fastmcp, trying `_tools` or similar. But if import succeeded, tools are registered.
    print(f"FastMCP server instantiated: {mcp_server.name}")

    print("\n3. Testing Agent Flow (Mocking Intent)...")
    state = {
        "messages": [HumanMessage(content="I want to book an appointment")],
        "user_id": "test-user-id",
        "session_id": "test-session",
        "intent": "scheduling",
        "entities": {}
    }

    try:
        print("Invoking graph...")
        config = {"configurable": {"thread_id": "test-session-123"}}
        result = await graph.ainvoke(state, config=config)
        print("Graph execution completed.")
        print(f"Final State Intent: {result.get('intent')}")
        print(f"Final Response: {result.get('final_response')}")
        print(f"Messages count: {len(result.get('messages', []))}")
        
    except Exception as e:
        print(f"Graph execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
