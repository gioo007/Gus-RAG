"""This module keeps the old prompt-based generation path for v1 queries and adds a
LangChain tool-calling agent for v2 queries. The agent executes the retrieval tool
when the Groq model decides it needs grounded evidence from the ingested corpus,
while preserving the original single-call flow for the older dashboard.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field, SecretStr

from app.core.config import settings
from app.services import retrieval

api_key = SecretStr(settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None
llm = ChatGroq(temperature=0, model=settings.LLM_MODEL, api_key=api_key)

PROMPT_TEMPLATE = """
Your name is Gus, a retrieval-augmented assistant built by Gio.

If: simple introductory/greetings questions, reply similarly

Else:
    Answer the question using only the context below. Do not add facts, examples, or explanations that aren't supported by the context, and don't guess at details the context doesn't cover.

    If the context is incomplete or doesn't address the question at all, you may add relevant knowledge from outside the context, but only after giving whatever grounded answer the context does support.
    Never blend outside knowledge into the grounded portion, always keep them separated and each section, and never imply it came from the provided documents.

    Keep your answers concise, well organized, and good looking when/if using markdown.

    Context:
    {context}"""


class RetrievalToolInput(BaseModel):
    question: str = Field(
        ...,
        description="The question to answer using the ingested document corpus.",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional session-scoped document filter. Use the current session id when supplied.",
    )


@tool(args_schema=RetrievalToolInput)
def retrieve_documents(question: str, session_id: str | None = None) -> str:
    """Search the ingested corpus for source passages that can answer a question grounded in the available documents."""
    docs = retrieval.retrieve(question, version="v2", session_id=session_id)
    payload = [
        {"page_content": doc.page_content, "metadata": doc.metadata}
        for doc in docs
    ]
    return json.dumps(payload)


def _deserialize_documents(payload: Any) -> list[Document]:
    if not payload:
        return []
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return []
    if not isinstance(payload, list):
        return []

    documents: list[Document] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        documents.append(
            Document(
                page_content=item.get("page_content", ""),
                metadata=item.get("metadata", {}) or {},
            )
        )
    return documents


def _dedupe_sources(chunks: list[Document]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    sources: list[dict[str, Any]] = []
    for chunk in chunks:
        source = chunk.metadata.get("source", "unknown")
        if source in seen:
            continue
        seen.add(source)
        sources.append({
            "source": source,
            "source_type": chunk.metadata.get("source_type"),
        })
    return sources


def run_agent(question: str, history: list | None = None, session_id: str | None = None) -> dict[str, Any]:
    """Run the Groq tool-calling agent for v2 queries using the current session's history."""
    messages: list[Any] = [SystemMessage(content=PROMPT_TEMPLATE.format(context=""))]
    messages.extend(history or [])
    messages.append(HumanMessage(content=question))

    model = llm.bind_tools([retrieve_documents])
    response = model.invoke(messages)
    tool_outputs: list[str] = []

    while getattr(response, "tool_calls", None):
        messages.append(response)
        for call in response.tool_calls:
            tool_name = call.get("name") if isinstance(call, dict) else getattr(call, "name", None)
            tool_args = call.get("args") if isinstance(call, dict) else getattr(call, "args", {})
            if tool_name != retrieve_documents.name:
                continue
            tool_args = dict(tool_args or {})
            tool_args.setdefault("question", question)
            tool_args.setdefault("session_id", session_id)
            tool_result = retrieve_documents.invoke(tool_args)
            tool_outputs.append(str(tool_result))
            messages.append(
                ToolMessage(
                    content=str(tool_result),
                    tool_call_id=call.get("id") if isinstance(call, dict) else getattr(call, "id", "tool-call"),
                    name=tool_name,
                )
            )
        response = model.invoke(messages)

    final_text = response.content if hasattr(response, "content") else str(response)
    docs: list[Document] = []
    for payload in tool_outputs:
        docs.extend(_deserialize_documents(payload))
    return {"answer": str(final_text), "sources": _dedupe_sources(docs)}


def generate(question: str, chunks: list | None = None, history: list | None = None, version: str = "v1", session_id: str | None = None) -> str:
    if version == "v2":
        return run_agent(question, history=history, session_id=session_id)["answer"]

    context = "\n\n".join(doc.page_content for doc in chunks or [])
    system = SystemMessage(content=PROMPT_TEMPLATE.format(context=context))
    response = llm.invoke([system, *(history or []), HumanMessage(content=question)])
    return str(response.content)
