from langchain_core.documents import Document
from app.services.vectorstore import vector_store

DEFAULT_K = 4


def retrieve(question: str, k: int = DEFAULT_K) -> list[Document]:
    #plain top-k similarity search for v1
    retriever = vector_store.as_retriever(search_kwargs={"k": k})
    return retriever.invoke(question)