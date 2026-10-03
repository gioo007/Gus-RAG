import uuid
from pathlib import Path
from typing import Annotated, Callable, Literal
from fastapi import APIRouter, Form, HTTPException, UploadFile
from app.models.schemas import DocumentSummary, IngestionResponse, WebIngestRequest
from app.services import ingestion, vectorstore, retrieval

router = APIRouter()

LoaderFn = Callable[[bytes, str], list]
LoaderSource = Literal["pdf", "docx", "notion"]

LOADER_DISPATCH: dict[str, tuple[LoaderSource, LoaderFn]] = {
    ".pdf": ("pdf", lambda data, name: ingestion.ingest_pdf(data, name)),
    ".docx": ("docx", lambda data, name: ingestion.ingest_docx(data, name)),
    ".zip": ("notion", lambda data, name: ingestion.ingest_notion(data, name)) #only supports/assumes notion zip exports
}


def store_chunks(chunks: list, source_type: str, session_id: str) -> None:
    for chunk in chunks:
        chunk.metadata["source_type"] = source_type
        chunk.metadata["session_id"] = session_id
    try:
        vectorstore.add_documents(chunks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store embeddings: {e}") from e

    retrieval.invalidate_bm25_cache(session_id)


@router.get("/", response_model=list[DocumentSummary])
async def list_documents(session_id: str | None = None):
    try:
        return vectorstore.list_documents(session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve documents: {e}") from e


#session_id must be Form() to match the multipart/form-data request
#to match the uploadfile form format
@router.post("/upload", response_model=IngestionResponse)
async def upload_document(file: UploadFile,session_id: Annotated[str | None, Form()] = None):
    session_id = session_id or str(uuid.uuid4())

    filename = file.filename or "unknown"
    extension = Path(filename).suffix.lower()
    dispatch = LOADER_DISPATCH.get(extension)

    if dispatch is None:
        supported = ", ".join(LOADER_DISPATCH)
        raise HTTPException(status_code=415,detail=f"Unsupported file type '{extension or 'unknown'}'. Supported:{supported}.")

    source_type, ingest_fn = dispatch
    file_bytes = await file.read()
    try:
        chunks = ingest_fn(file_bytes, filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    store_chunks(chunks, source_type, session_id)

    return IngestionResponse(
        source=filename,
        source_type=source_type,
        chunk_count=len(chunks),
        sample_chunk=chunks[0].page_content[:200] if chunks else None,
        session_id=session_id
    )


@router.post("/web", response_model=IngestionResponse)
async def ingest_web_page(payload: WebIngestRequest):
    session_id = payload.session_id or str(uuid.uuid4())

    try:
        chunks = ingestion.ingest_web(str(payload.url))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    store_chunks(chunks, "web", session_id)

    return IngestionResponse(
        source=str(payload.url),
        source_type="web",
        chunk_count=len(chunks),
        sample_chunk=chunks[0].page_content[:200] if chunks else None,
        session_id=session_id
    )


@router.delete("/{source_name:path}")
async def delete_document_by_name(source_name: str, session_id: str | None = None):
    result = vectorstore.delete_by_source(source_name, session_id=session_id)

    if result["deleted_count"] == 0:
        raise HTTPException(status_code=404, detail=f"No chunks found for source '{source_name}'.")

    retrieval.invalidate_bm25_cache(session_id)

    return {
        "detail": f"Successfully deleted '{source_name}' and its {result['deleted_count']} vector chunk(s).",
        "collection_id": result["collection_id"]
    }