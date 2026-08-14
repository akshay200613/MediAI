"""
RAG Prompt Builder – assembles context-augmented prompts for the LLM.
"""

from core.ai.llm.client import Message


def build_rag_prompt(
    query: str,
    context_chunks: list[str],
    conversation_history: list[Message] | None = None,
    source_metadata: list[dict] | None = None,
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
        source_metadata: Optional metadata list parallel to context_chunks
                         (category, title, hospital, etc.)

    Returns:
        List of Message objects to send to the LLM
    """
    messages: list[Message] = []

    # Include conversation history (excluding system messages)
    if conversation_history:
        for msg in conversation_history:
            if msg.role != "system":
                messages.append(msg)

    # Build enriched context block — include metadata labels when available
    context_parts: list[str] = []
    for i, chunk in enumerate(context_chunks):
        meta = (source_metadata or [{}])[i] if source_metadata else {}
        labels: list[str] = []
        if meta.get("category"):
            labels.append(f"Category: {meta['category']}")
        if meta.get("title"):
            labels.append(f"Source: {meta['title']}")
        if meta.get("hospital_name") or meta.get("hospital"):
            labels.append(f"Hospital: {meta.get('hospital_name') or meta.get('hospital')}")
        header = f"[Source {i + 1}]"
        if labels:
            header += " " + " | ".join(labels)
        context_parts.append(f"{header}\n{chunk}")

    context_block = "\n\n---\n\n".join(context_parts)

    augmented_query = (
        "You are a medical knowledge assistant. Answer the question using ONLY the "
        "context provided below. Do not invent information that is not present in the context.\n\n"
        "Rules:\n"
        "1. Cite the specific source(s) using [Source N] inline where you use information from them.\n"
        "2. If the context is insufficient, clearly say: "
        '"The knowledge base does not contain enough information to answer this question accurately."\n'
        "3. Prefer specific facts, numbers, and named entities over vague statements.\n"
        "4. Write in clear, professional medical language.\n\n"
        f"=== RETRIEVED CONTEXT ===\n{context_block}\n\n"
        f"=== QUESTION ===\n{query}"
    )

    messages.append(Message(role="user", content=augmented_query))
    return messages
