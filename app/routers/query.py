from fastapi import APIRouter, HTTPException
from app.models.schemas import QueryRequest, QueryResponse, SourceInfo
from app.services import generation, retrieval

router = APIRouter()


@router.post("/", response_model=QueryResponse)
async def ask_question(payload: QueryRequest):
    try:
        chunks = retrieval.retrieve(payload.question, k=payload.k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve documents: {e}") from e

    try:
        answer = generation.generate(payload.question, chunks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {e}") from e

    #list distinct sources
    seen = set()
    sources = []
    for chunk in chunks:
        source = chunk.metadata.get("source", "unknown")
        if source in seen:
            continue
        seen.add(source)
        sources.append(SourceInfo(source=source, source_type=chunk.metadata.get("source_type")))

    return QueryResponse(answer=answer, sources=sources)