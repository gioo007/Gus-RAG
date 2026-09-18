from typing import Literal
from pydantic import BaseModel, Field, HttpUrl


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


class QueryRequest(BaseModel):
    question: str
    k: int = Field(default=4, gt=0, le=10)
    session_id: str | None = None
 
 
class SourceInfo(BaseModel):
    source: str
    source_type: str | None = None
 
 
class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]
    session_id: str