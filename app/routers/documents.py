from pathlib import Path
from typing import Callable, Literal
from fastapi import APIRouter, HTTPException, UploadFile
from app.models.schemas import IngestionResponse, WebIngestRequest
from app.services import ingestion

router = APIRouter()

LoaderFn = Callable[[bytes, str], list]
LoaderSource = Literal["pdf", "docx", "notion"]

LOADER_DISPATCH: dict[str, tuple[LoaderSource, LoaderFn]] = {
    ".pdf": ("pdf", lambda data, name: ingestion.ingest_pdf(data, name)),
    ".docx": ("docx", lambda data, name: ingestion.ingest_docx(data, name)),
    ".zip": ("notion", lambda data, name: ingestion.ingest_notion(data)) #only supports/assumes notion zip exports
}


@router.post("/upload", response_model=IngestionResponse)
async def upload_document(file: UploadFile):
    
    filename = file.filename or "unknown"
    extension = Path(filename).suffix.lower()
    dispatch = LOADER_DISPATCH.get(extension)

    if dispatch is None:
        supported = " ".join(LOADER_DISPATCH)
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

    return IngestionResponse(
        source=str(payload.url),
        source_type="web",
        chunk_count=len(chunks),
        sample_chunk=chunks[0].page_content[:200] if chunks else None
    )