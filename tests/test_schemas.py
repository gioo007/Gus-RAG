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
    response = IngestionResponse(source="x", source_type=source_type, chunk_count=1, session_id="abc")
    assert response.source_type == source_type


def test_query_request_defaults_version_to_v1_and_session_id_to_none():
    request = QueryRequest(question="what is this?")
    assert request.version == "v1"
    assert request.session_id is None


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_query_request_accepts_supported_versions(version):
    request = QueryRequest(question="q", version=version)
    assert request.version == version


def test_query_request_rejects_an_unknown_version():
    with pytest.raises(ValidationError):
        QueryRequest(question="q", version="v3") #type: ignore (schema validation should fail)


def test_query_response_holds_answer_sources_and_session_id():
    response = QueryResponse(
        answer="the answer",
        sources=[SourceInfo(source="a.pdf", source_type="pdf")],
        session_id="abc"
    )
    assert response.sources[0].source == "a.pdf"
