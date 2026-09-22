import pytest
from pydantic import HttpUrl, ValidationError

from backend.app.models.schemas import (
    DocumentSummary,
    IngestionResponse,
    QueryRequest,
    QueryResponse,
    SourceInfo,
    WebIngestRequest,
)


def test_web_ingest_request_accepts_a_valid_url():
    request = WebIngestRequest(url=HttpUrl("https://en.wikipedia.org/wiki/Kiwifruit"))
    assert str(request.url) == "https://en.wikipedia.org/wiki/Kiwifruit"


def test_web_ingest_request_rejects_a_non_url_string():
    with pytest.raises(ValidationError):
        WebIngestRequest(url=HttpUrl("not a url"))


def test_document_summary_allows_a_missing_source_type():
    summary = DocumentSummary(source="legacy.pdf", chunk_count=5, source_type=None)
    assert summary.source_type is None


def test_ingestion_response_rejects_an_unknown_source_type():
    with pytest.raises(ValidationError):
        IngestionResponse(source="x.pdf", source_type="csv", chunk_count=1) # type: ignore


@pytest.mark.parametrize("source_type", ["pdf", "docx", "web", "notion"])
def test_ingestion_response_accepts_every_supported_source_type(source_type):
    response = IngestionResponse(source="x", source_type=source_type, chunk_count=1)
    assert response.source_type == source_type


def test_query_request_defaults_k_to_four_and_session_id_to_none():
    request = QueryRequest(question="what is this?")
    assert request.k == 4
    assert request.session_id is None


@pytest.mark.parametrize("k", [0, -1, 11, 100])
def test_query_request_rejects_k_outside_one_to_ten(k):
    with pytest.raises(ValidationError):
        QueryRequest(question="q", k=k)


@pytest.mark.parametrize("k", [1, 5, 10])
def test_query_request_accepts_k_within_bounds(k):
    request = QueryRequest(question="q", k=k)
    assert request.k == k


def test_query_response_holds_answer_sources_and_session_id():
    response = QueryResponse(
        answer="the answer",
        sources=[SourceInfo(source="a.pdf", source_type="pdf")],
        session_id="abc"
    )
    assert response.sources[0].source == "a.pdf"
