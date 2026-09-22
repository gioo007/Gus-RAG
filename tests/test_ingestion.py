import zipfile
from types import SimpleNamespace

import pytest

from app.services import ingestion


def test_ingest_pdf_extracts_text_and_tags_the_source(sample_pdf_bytes):
    chunks = ingestion.ingest_pdf(sample_pdf_bytes, "sample.pdf")

    assert len(chunks) >= 1
    assert all(chunk.metadata["source"] == "sample.pdf" for chunk in chunks)
    joined = " ".join(chunk.page_content for chunk in chunks)
    assert "capstone" in joined.lower()


def test_ingest_pdf_raises_a_value_error_when_the_loader_returns_no_pages(monkeypatch):
    monkeypatch.setattr(ingestion, "PyPDFLoader", lambda path: SimpleNamespace(load=lambda: []))

    with pytest.raises(ValueError, match="No extractable text"):
        ingestion.ingest_pdf(b"irrelevant bytes", "empty.pdf")


def test_ingest_docx_extracts_text_and_tags_the_source(sample_docx_bytes):
    chunks = ingestion.ingest_docx(sample_docx_bytes, "sample.docx")

    assert len(chunks) >= 1
    assert all(chunk.metadata["source"] == "sample.docx" for chunk in chunks)
    joined = " ".join(chunk.page_content for chunk in chunks)
    assert "capstone" in joined.lower()


def test_ingest_docx_raises_a_value_error_when_the_loader_returns_no_pages(monkeypatch):
    monkeypatch.setattr(ingestion, "Docx2txtLoader", lambda path: SimpleNamespace(load=lambda: []))

    with pytest.raises(ValueError, match="No extractable text"):
        ingestion.ingest_docx(b"irrelevant bytes", "empty.docx")


def test_ingest_web_extracts_and_chunks_the_page_text(monkeypatch):
    monkeypatch.setattr(ingestion.trafilatura, "fetch_url", lambda url: "<html>raw</html>")
    monkeypatch.setattr(ingestion.trafilatura, "extract", lambda html: "Some real extracted article text.")

    chunks = ingestion.ingest_web("https://example.com/article")

    assert len(chunks) == 1
    assert chunks[0].metadata["source"] == "https://example.com/article"
    assert chunks[0].page_content == "Some real extracted article text."


def test_ingest_web_raises_when_the_page_cannot_be_fetched(monkeypatch):
    monkeypatch.setattr(ingestion.trafilatura, "fetch_url", lambda url: None)

    with pytest.raises(ValueError, match="Could not load content"):
        ingestion.ingest_web("https://example.com/dead-link")


def test_ingest_web_raises_when_extraction_finds_no_content(monkeypatch):
    monkeypatch.setattr(ingestion.trafilatura, "fetch_url", lambda url: "<html></html>")
    monkeypatch.setattr(ingestion.trafilatura, "extract", lambda html: None)

    with pytest.raises(ValueError, match="No content found"):
        ingestion.ingest_web("https://example.com/empty")


def test_ingest_notion_extracts_pages_and_tags_every_chunk_with_the_zip_filename(sample_notion_zip_bytes):
    chunks = ingestion.ingest_notion(sample_notion_zip_bytes, "my_export.zip")

    assert len(chunks) >= 1
    assert all(chunk.metadata["source"] == "my_export.zip" for chunk in chunks)
    joined = " ".join(chunk.page_content for chunk in chunks)
    assert "notion export" in joined.lower()


def test_ingest_notion_rejects_a_file_that_is_not_a_real_zip():
    with pytest.raises(ValueError, match="not a valid .zip"):
        ingestion.ingest_notion(b"this is not a zip file", "fake.zip")


def test_ingest_notion_raises_when_the_zip_has_no_markdown_files(tmp_path):
    empty_zip_path = tmp_path / "empty.zip"
    with zipfile.ZipFile(empty_zip_path, "w") as zf:
        zf.writestr("readme.txt", "no markdown here")

    with pytest.raises(ValueError, match="No Markdown files found"):
        ingestion.ingest_notion(empty_zip_path.read_bytes(), "empty.zip")
