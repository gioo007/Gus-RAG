from typing import Literal

from pydantic import BaseModel, HttpUrl


class WebIngestRequest(BaseModel):
    url: HttpUrl


class IngestionResponse(BaseModel):
    source: str
    source_type: Literal["pdf", "docx", "web", "notion"]
    chunk_count: int
    sample_chunk: str | None = None