""""
v2: self-query (natural-language metadata filtering) + MMR as the dense retriever, ensembled
    with BM25 as the sparse retriever (this pairing is the hybrid search step), then a
    cross-encoder rerank down to k, then contextual compression to trim each chunk to just
    its relevant sentences. An optional multi-hop pass decomposes the question first when it
    needs more than one retrieval to answer.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any

from langchain_classic.chains.query_constructor.schema import AttributeInfo
from langchain_classic.retrievers.document_compressors import LLMChainExtractor
from langchain_classic.retrievers.ensemble import EnsembleRetriever
from langchain_classic.retrievers.self_query.base import SelfQueryRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_groq import ChatGroq
from langchain_postgres.translator import PGVectorTranslator
from langchain_cohere import CohereRerank
from pydantic import SecretStr

from app.core.config import settings
from app.services.vectorstore import get_all_documents, vector_store


BM25_CACHE_TTL_SECONDS = 600  #rebuild the BM25 index at most every 5 minutes
BM25_CACHE_MAX_SESSIONS = 20  #evict the LRU sessions' indexes past this many cached

METADATA_FIELD_INFO = [
    AttributeInfo(
        name="source",
        description="The filename or source URL the chunk was ingested from.",
        type="string"
    ),
    AttributeInfo(
        name="source_type",
        description="The type of the source document: 'pdf', 'docx', 'web', or 'notion'.",
        type="string"
    )
    #didnt add session_id to prevent llm from messing with it, its set in the vector retriever func
    #preventing any type of query injections
]

DECOMPOSITION_PROMPT = PromptTemplate.from_template(
    """You are a query planner for a document question-answering system.

Decide whether the question below needs to be broken into multiple simpler sub-questions to
retrieve everything needed to answer it (multi-hop), or whether it can be retrieved for
directly (single-hop).

If single-hop, respond with exactly one line: the original question, unchanged.
If multi-hop, respond with between 2 and {max_subquestions} lines, each a standalone
sub-question that can be retrieved for independently, together covering everything the
original question needs. Respond with nothing but the question(s), one per line. No
numbering, no commentary.

Question: {question}"""
)

# Lazily built/loaded so a deployment running strategy="v1" never pays for these.
retrieval_llm: ChatGroq | None = None
#distinct cache entry per every session_id, ordereddict enforces lru eviction
bm25_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()


def touch_bm25_cache(cache_key: str) -> None:
    #mark cache_key as most-recently-used and evict the oldest entries past the cap
    bm25_cache.move_to_end(cache_key)
    while len(bm25_cache) > BM25_CACHE_MAX_SESSIONS:
        bm25_cache.popitem(last=False)


def invalidate_bm25_cache(session_id: str | None = None) -> None:
    """Call this after ingesting or deleting documents so the next v2 query rebuilds the
    BM25 index immediately instead of waiting out the TTL. Not wired in automatically --
    that hook belongs in the documents router (add a call here to add_documents/delete_by_source's
    callers if you want instant invalidation instead of the TTL)."""
    cache_key = session_id or "__all__"
    bm25_cache[cache_key] = {"retriever": None, "built_at": 0.0}
    touch_bm25_cache(cache_key)


def get_retrieval_llm() -> ChatGroq:
    global retrieval_llm
    if retrieval_llm is None:
        api_key = SecretStr(settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None
        retrieval_llm = ChatGroq(temperature=0, model=settings.LLM_MODEL, api_key=api_key)
    return retrieval_llm


def get_bm25_retriever(k: int, session_id: str | None = None) -> BM25Retriever | None:
    cache_key = session_id or "__all__"
    cache = bm25_cache.setdefault(cache_key, {"retriever": None, "built_at": 0.0})
    touch_bm25_cache(cache_key)
    now = time.monotonic()
    stale = (cache["retriever"] is None or (now - cache["built_at"]) > BM25_CACHE_TTL_SECONDS)
    if stale:
        docs = get_all_documents(session_id=session_id)
        cache["retriever"] = BM25Retriever.from_documents(docs) if docs else None
        cache["built_at"] = now

    retriever = cache["retriever"]
    if retriever is not None:
        retriever.k = k
    return retriever


def build_vector_retriever(fetch_k: int, session_id: str | None = None) -> BaseRetriever:
    #metadata filtering + mmr in one retriever
    search_kwargs: dict[str, Any] = {"k": fetch_k}
    if session_id is not None:
        search_kwargs["filter"] = {"session_id": session_id}

    return SelfQueryRetriever.from_llm(
        llm=get_retrieval_llm(),
        vectorstore=vector_store,
        document_contents="Chunks of user-uploaded documents: PDFs, Word docs, Notion exports, and web pages.",
        metadata_field_info=METADATA_FIELD_INFO,
        structured_query_translator=PGVectorTranslator(),
        search_type="mmr",
        search_kwargs=search_kwargs
    )


def build_hybrid_retriever(fetch_k: int, session_id: str | None = None) -> BaseRetriever:
    vector_side = build_vector_retriever(fetch_k, session_id=session_id)
    bm25_side = get_bm25_retriever(fetch_k, session_id=session_id)
    if bm25_side is None:
        #no documents ingested yet (or the corpus fetch came back empty) -- fall back to dense-only
        return vector_side
    return EnsembleRetriever(
        retrievers=[vector_side, bm25_side],
        weights=[1 - settings.BM25_WEIGHT, settings.BM25_WEIGHT]
    )


def decompose_question(question: str) -> list[str]:
    llm = get_retrieval_llm()
    prompt = DECOMPOSITION_PROMPT.format(
        question=question, max_subquestions=settings.MULTI_HOP_MAX_SUBQUESTIONS
    )
    response = llm.invoke(prompt)
    lines = [line.strip("-* ").strip() for line in str(response.content).splitlines()]
    sub_questions = [line for line in lines if line]
    return sub_questions[: settings.MULTI_HOP_MAX_SUBQUESTIONS] or [question]


def dedupe(docs: list[Document]) -> list[Document]:
    seen: set[tuple[str, str]] = set()
    deduped: list[Document] = []
    for doc in docs:
        key = (doc.metadata.get("source", ""), doc.page_content)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(doc)
    return deduped


def rerank(question: str, docs: list[Document], top_k: int) -> list[Document]:
    if not docs:
        return docs
    reranker = CohereRerank(model="rerank-v3.5", top_n=top_k, cohere_api_key=SecretStr(settings.COHERE_API_KEY))
    reranked = reranker.compress_documents(docs, query=question)
    return [doc for doc in reranked[:top_k]]


def compress(question: str, docs: list[Document]) -> list[Document]:
    if not docs:
        return docs
    compressor = LLMChainExtractor.from_llm(get_retrieval_llm())
    compressed = compressor.compress_documents(docs, question)
    return list(compressed) or docs


def retrieve_v1(question: str, k: int, session_id: str | None = None) -> list[Document]:
    #plain top-k similarity search -- the eval harness baseline, unchanged
    search_kwargs: dict[str, Any] = {"k": k}
    if session_id is not None:
        search_kwargs["filter"] = {"session_id": session_id}
    retriever = vector_store.as_retriever(search_kwargs=search_kwargs)
    return retriever.invoke(question)


def retrieve_v2(question: str, k: int, session_id: str | None = None) -> list[Document]:
    fetch_k = k * settings.RETRIEVAL_FETCH_K_MULTIPLIER
    sub_questions = decompose_question(question)
    retriever = build_hybrid_retriever(fetch_k, session_id=session_id)

    candidates: list[Document] = []
    for sub_question in sub_questions:
        candidates.extend(retriever.invoke(sub_question))

    if session_id is not None:
        #recheck file's session id regardless of which retriever it came from (just in case)
        candidates = [doc for doc in candidates if doc.metadata.get("session_id") == session_id]

    deduped = dedupe(candidates)
    reranked = rerank(question, deduped, top_k=k)
    return compress(question, reranked)


def retrieve(question: str, version: str = "v1", k: int | None = None, session_id: str | None = None) -> list[Document]:

    #this lets the frontend call `retrieve(question, "v2")` while preserving
    #the ability of eval harness to try different k's with v2
    
    strategy = version or settings.RETRIEVAL_STRATEGY
    effective_k = k if k is not None else settings.DEFAULT_K

    if strategy == "v2":
        return retrieve_v2(question, effective_k, session_id=session_id)
    return retrieve_v1(question, effective_k, session_id=session_id)