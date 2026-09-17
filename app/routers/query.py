from fastapi import APIRouter, HTTPException
from app.models.schemas import QueryRequest, QueryResponse, SourceInfo
from app.services import generation, retrieval, chat_history
import uuid

router = APIRouter()

MAX_HISTORY_MESSAGES = 30  #number of messages to keep in history

@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    session_id = request.session_id or str(uuid.uuid4())
    with chat_history.get_history(session_id) as history:
        recent = history.messages[-MAX_HISTORY_MESSAGES:]

        try:
            chunks = retrieval.retrieve(request.question, k=request.k)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to retrieve documents: {e}") from e

        try:
            answer = generation.generate(request.question, chunks, recent)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate answer: {e}") from e

        history.add_user_message(request.question)
        history.add_ai_message(answer)

    #list distinct sources
    seen = set()
    sources = []
    for chunk in chunks:
        source = chunk.metadata.get("source", "unknown")
        if source in seen:
            continue
        seen.add(source)
        sources.append(SourceInfo(source=source, source_type=chunk.metadata.get("source_type")))

    return QueryResponse(answer=answer, sources=sources, session_id=session_id)