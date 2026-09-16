from typing import Literal

from pydantic import BaseModel, HttpUrl


class WebIngestRequest(BaseModel):
    url: HttpUrl

class DocumentSummary(BaseModel):
    source: str
    source_type: str | None = None
    chunk_count: int

class IngestionResponse(BaseModel):
    source: str
    source_type: Literal["pdf", "docx", "web", "notion"]
    chunk_count: int
    sample_chunk: str | None = None