from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from pydantic import SecretStr

from app.core.config import settings

MODEL_NAME = "openai/gpt-oss-120b"

api_key = SecretStr(settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None
llm = ChatGroq(temperature=0, model=MODEL_NAME, api_key=api_key)

PROMPT_TEMPLATE = """Your name is Gus. Use the following pieces of context to answer the question at the end.
If you don't know the answer, just say that you don't know. Keep the answer concise.

{context}"""

prompt = PromptTemplate.from_template(PROMPT_TEMPLATE)


def generate(question: str, chunks: list, history: list | None = None) -> str:
    context = "\n\n".join(doc.page_content for doc in chunks)
    system = SystemMessage(content=PROMPT_TEMPLATE.format(context=context))
    response = llm.invoke([system, *(history or []), HumanMessage(content=question)])
    return str(response.content)