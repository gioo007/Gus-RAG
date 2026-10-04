"""Generation layer for Gus.

v1 queries use a single prompt based call: retrieved chunks are stuffed into the
system prompt and answered by Groq in one pass.

v2 queries use a LangChain create_agent agent. The model decides when to call the
retrieve_documents tool, and the current session id travels through the agent's
runtime context, so the model can never read or override it.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain.tools import ToolRuntime, tool
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from pydantic import SecretStr

from app.core.config import settings
from app.services import retrieval

api_key = SecretStr(settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None
llm = ChatGroq(temperature=0, model=settings.LLM_MODEL, api_key=api_key)

#maximum number of retrieve_documents calls the agent may make per question.
MAX_RETRIEVALS = 3

PROMPT_TEMPLATE = """
Your name is Gus, a retrieval-augmented assistant built by Gio. You answer questions about the documents the user has uploaded, and you can also chat normally.
 
Questions about you (who you are, what you can do), greetings, thanks, and other small talk:
    Answer directly and naturally in a sentence or two. Ignore the context below entirely. Do not mention context, missing information, or sources, and do not split your answer into sections.
    About you: you answer questions from the user's uploaded documents (PDFs, Word files, Notion exports, web pages), show which sources you used, and remember the conversation within a session.
 
Questions about the user's documents, or that clearly need them:
    Answer using only the context below. Do not add facts, examples, or explanations that aren't supported by the context, and don't guess at details the context doesn't cover.
 
    If the context fully answers the question, just answer. Do not mention the context or add extra sections.
 
    If the context is incomplete or doesn't address the question, give whatever grounded answer it does support first. After that you may add relevant knowledge from outside the context in a clearly separate section, and never imply it came from the provided documents. Never blend outside knowledge into the grounded part.
 
Keep your answers concise, well organized, and good looking when/if using markdown.
 
Context:
{context}"""
 
AGENT_PROMPT = """
Your name is Gus, a retrieval-augmented assistant built by Gio. You answer questions about the documents the user has uploaded, and you can also chat normally.
 
Questions about you (who you are, what you can do), greetings, thanks, and other small talk:
    Answer directly and naturally in a sentence or two, without calling any tool. Do not mention context, missing information, or sources, and do not split your answer into sections.
    About you: you answer questions from the user's uploaded documents (PDFs, Word files, Notion exports, web pages), show which sources you used, and remember the conversation within a session.
 
Questions about the user's documents, or that clearly need them:
    Call the retrieve_documents tool first. You may call it again with a rephrased or narrower question if the first results are incomplete.
 
    Answer using only what the tool returns. Do not add facts the passages do not support, and do not guess at details they do not cover. If the passages fully answer the question, just answer with no extra sections.
 
    If the passages are incomplete or empty, give whatever grounded answer they support first. After that you may add relevant outside knowledge in a clearly separate section, and never imply it came from the documents. Never blend outside knowledge into the grounded part.
 
    If the tool reports that retrieval failed or the search limit was reached, say so plainly instead of presenting an ungrounded answer as if it were grounded.
 
Keep answers concise and well organized, using markdown where it helps."""



@dataclass
class AgentContext:
    """Per request values the agent's tools can read. Never exposed to the model."""
    session_id: str


@tool(response_format="content_and_artifact")
def retrieve_documents(question: str, runtime: ToolRuntime[AgentContext]) -> tuple[str, list[Document]]:
    """Search the user's ingested documents for passages relevant to a question."""
    session_id = runtime.context.session_id
    if not session_id:
        raise ValueError("session_id missing from agent context")

    docs = retrieval.retrieve(question, version="v2", session_id=session_id)
    if not docs:
        return "No relevant passages found.", []

    content = "\n\n".join(
        f"[{i}] (source: {doc.metadata.get('source', 'unknown')})\n{doc.page_content}"
        for i, doc in enumerate(docs, 1)
    )
    #content goes to the model, docs ride along on ToolMessage.artifact for sources.
    return content, docs


def dedupe_sources(chunks: list[Document]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    sources: list[dict[str, Any]] = []
    for chunk in chunks:
        source = chunk.metadata.get("source", "unknown")
        if source in seen:
            continue
        seen.add(source)
        sources.append({"source": source, "source_type": chunk.metadata.get("source_type")})
    return sources


@lru_cache(maxsize=1)
def get_agent():
    """Build the v2 agent once, on first use, so importing this module has no side effects."""
    return create_agent(
        model=llm,
        tools=[retrieve_documents],
        system_prompt=AGENT_PROMPT,
        context_schema=AgentContext,
        middleware=[ToolCallLimitMiddleware(tool_name="retrieve_documents", run_limit=MAX_RETRIEVALS, exit_behavior="continue")]
    )


def run_agent(question: str, history: list | None = None, *,session_id: str) -> dict[str, Any]:
    """Run the v2 agent for one question using the current session's history."""
    input_messages = [*(history or []), HumanMessage(content=question)]

    result = get_agent().invoke({"messages": input_messages}, context=AgentContext(session_id=session_id))

    # Only look at messages produced during this turn when collecting sources.
    new_messages = result["messages"][len(input_messages):]
    docs: list[Document] = [
        doc
        for message in new_messages
        if isinstance(message, ToolMessage) and isinstance(message.artifact, list)
        for doc in message.artifact
    ]

    return {
        "answer": str(result["messages"][-1].content),
        "sources": dedupe_sources(docs)
    }


def generate(question: str, chunks: list | None = None, history: list | None = None) -> str:
    """v1 path: stuff retrieved chunks into the prompt and answer in a single call."""
    context = "\n\n".join(doc.page_content for doc in chunks or [])
    system = SystemMessage(content=PROMPT_TEMPLATE.format(context=context))
    response = llm.invoke([system, *(history or []), HumanMessage(content=question)])
    return str(response.content)