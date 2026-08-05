"""
RAG Prompt Builder – assembles context-augmented prompts for the LLM.
"""

from core.ai.llm.client import Message


def build_rag_prompt(
    query: str,
    context_chunks: list[str],
    conversation_history: list[Message] | None = None,
) -> list[Message]:
    """
    Build the message list for a RAG query.

    Structure:
    1. System message (handled separately in LLM client)
    2. Conversation history (prior turns)
    3. Context-augmented user message

    Args:
        query: The user's question
        context_chunks: Retrieved document chunks
        conversation_history: Prior conversation turns

    Returns:
        List of Message objects to send to the LLM
    """
    messages: list[Message] = []

    # Include conversation history (excluding system messages)
    if conversation_history:
        for msg in conversation_history:
            if msg.role != "system":
                messages.append(msg)

    # Build context block
    context_block = "\n\n---\n\n".join(
        f"[Source {i+1}]\n{chunk}" for i, chunk in enumerate(context_chunks)
    )

    augmented_query = (
        f"Use the following context to answer the question. "
        f"If the context doesn't contain the answer, say so clearly.\n\n"
        f"=== CONTEXT ===\n{context_block}\n"
        f"=== QUESTION ===\n{query}"
    )

    messages.append(Message(role="user", content=augmented_query))
    return messages
