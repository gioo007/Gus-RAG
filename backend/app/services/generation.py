from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from pydantic import SecretStr

from app.core.config import settings

api_key = SecretStr(settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None
llm = ChatGroq(temperature=0, model=settings.LLM_MODEL, api_key=api_key)

PROMPT_TEMPLATE = """Your name is Gus, a retrieval-augmented assistant built by Gio.

Answer the question using only the context below. Do not add facts, examples, or explanations that aren't supported by the context, and don't guess at details the context doesn't cover.

If the context is incomplete or doesn't address the question at all, you may add relevant knowledge from outside the context, but only after giving whatever grounded answer the context does support. 
Never blend outside knowledge into the grounded portion, always keep them separated and each section, and never imply it came from the provided documents.

Keep your answers concise, well organized, and good looking when/if using markdown.

Context:
{context}"""


def generate(question: str, chunks: list, history: list | None = None) -> str:
    context = "\n\n".join(doc.page_content for doc in chunks)
    system = SystemMessage(content=PROMPT_TEMPLATE.format(context=context))
    response = llm.invoke([system, *(history or []), HumanMessage(content=question)])
    return str(response.content)