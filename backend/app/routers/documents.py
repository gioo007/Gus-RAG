from pathlib import Path
from typing import Callable, Literal
from fastapi import APIRouter, HTTPException, UploadFile
from app.models.schemas import DocumentSummary, IngestionResponse, WebIngestRequest
from app.services import ingestion, vectorstore

router = APIRouter()

LoaderFn = Callable[[bytes, str], list]
LoaderSource = Literal["pdf", "docx", "notion"]

LOADER_DISPATCH: dict[str, tuple[LoaderSource, LoaderFn]] = {
    ".pdf": ("pdf", lambda data, name: ingestion.ingest_pdf(data, name)),
    ".docx": ("docx", lambda data, name: ingestion.ingest_docx(data, name)),
    ".zip": ("notion", lambda data, name: ingestion.ingest_notion(data, name)) #only supports/assumes notion zip exports
}

def store_chunks(chunks: list, source_type: str) -> None:
    for chunk in chunks:
        chunk.metadata["source_type"] = source_type
    try:
        vectorstore.add_documents(chunks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store embeddings: {e}") from e


@router.get("", response_model=list[DocumentSummary])
async def list_documents():
    try:
        return vectorstore.list_documents()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve documents: {e}") from e


@router.post("/upload", response_model=IngestionResponse)
async def upload_document(file: UploadFile):
    
    filename = file.filename or "unknown"
    extension = Path(filename).suffix.lower()
    dispatch = LOADER_DISPATCH.get(extension)

    if dispatch is None:
        supported = ", ".join(LOADER_DISPATCH)
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{extension or 'unknown'}'. Supported:{supported}."
        )

    source_type, ingest_fn = dispatch
    file_bytes = await file.read()
    try:
        chunks = ingest_fn(file_bytes, filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    store_chunks(chunks, source_type)

    return IngestionResponse(
        source=filename,
        source_type=source_type,
        chunk_count=len(chunks),
        sample_chunk=chunks[0].page_content[:200] if chunks else None
    )


@router.post("/web", response_model=IngestionResponse)
async def ingest_web_page(payload: WebIngestRequest):
    try:
        chunks = ingestion.ingest_web(str(payload.url))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    
    store_chunks(chunks, "web")

    return IngestionResponse(
        source=str(payload.url),
        source_type="web",
        chunk_count=len(chunks),
        sample_chunk=chunks[0].page_content[:200] if chunks else None
    )


@router.delete("/{source_name:path}")
async def delete_document_by_name(source_name: str):
    result = vectorstore.delete_by_source(source_name)
 
    if result["deleted_count"] == 0:
        raise HTTPException(
            status_code=404, detail=f"No chunks found for source '{source_name}'."
        )
 
    return {
        "detail": f"Successfully deleted '{source_name}' and its {result['deleted_count']} vector chunk(s).",
        "collection_id": result["collection_id"],
    }