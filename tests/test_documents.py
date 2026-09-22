from langchain_core.documents import Document

from app.services import ingestion, vectorstore


def test_list_documents_returns_vectorstore_summaries(client, monkeypatch):
    fake_rows = [{"source": "a.pdf", "source_type": "pdf", "chunk_count": 3}]
    monkeypatch.setattr(vectorstore, "list_documents", lambda: fake_rows)

    response = client.get("/documents/")

    assert response.status_code == 200
    assert response.json() == fake_rows


def test_list_documents_returns_500_on_db_failure(client, monkeypatch):
    def boom():
        raise RuntimeError("connection lost")
    monkeypatch.setattr(vectorstore, "list_documents", boom)

    response = client.get("/documents/")

    assert response.status_code == 500
    assert "connection lost" in response.json()["detail"]


def test_upload_pdf_dispatches_to_ingest_pdf_and_stores_chunks(client, monkeypatch):
    fake_chunks = [Document(page_content="hello world", metadata={"source": "test.pdf"})]
    monkeypatch.setattr(ingestion, "ingest_pdf", lambda data, name: fake_chunks)
    stored = {}
    monkeypatch.setattr(vectorstore, "add_documents", lambda chunks: stored.setdefault("chunks", chunks))

    response = client.post(
        "/documents/upload",
        files={"file": ("test.pdf", b"%PDF-1.4 fake", "application/pdf")}
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "source": "test.pdf",
        "source_type": "pdf",
        "chunk_count": 1,
        "sample_chunk": "hello world"
    }
    assert stored["chunks"][0].metadata["source_type"] == "pdf"


def test_upload_docx_dispatches_to_ingest_docx(client, monkeypatch):
    fake_chunks = [Document(page_content="a docx chunk")]
    monkeypatch.setattr(ingestion, "ingest_docx", lambda data, name: fake_chunks)
    monkeypatch.setattr(vectorstore, "add_documents", lambda chunks: None)

    response = client.post(
        "/documents/upload",
        files={"file": ("notes.docx", b"fake docx bytes", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )

    assert response.status_code == 200
    assert response.json()["source_type"] == "docx"


def test_upload_zip_dispatches_to_ingest_notion(client, monkeypatch):
    fake_chunks = [Document(page_content="a notion page")]
    monkeypatch.setattr(ingestion, "ingest_notion", lambda data, name: fake_chunks)
    monkeypatch.setattr(vectorstore, "add_documents", lambda chunks: None)

    response = client.post(
        "/documents/upload",
        files={"file": ("export.zip", b"PK fake zip bytes", "application/zip")}
    )

    assert response.status_code == 200
    assert response.json()["source_type"] == "notion"


def test_upload_rejects_an_unsupported_extension(client):
    response = client.post(
        "/documents/upload",
        files={"file": ("song.mp3", b"fake audio", "audio/mpeg")}
    )

    assert response.status_code == 415
    detail = response.json()["detail"]
    assert ".pdf" in detail
    assert ".docx" in detail
    assert ".zip" in detail


def test_upload_returns_422_when_the_loader_rejects_the_file(client, monkeypatch):
    def fail(data, name):
        raise ValueError(f"No extractable text found in '{name}'.")
    monkeypatch.setattr(ingestion, "ingest_pdf", fail)

    response = client.post(
        "/documents/upload",
        files={"file": ("empty.pdf", b"%PDF-1.4", "application/pdf")}
    )

    assert response.status_code == 422
    assert "empty.pdf" in response.json()["detail"]


def test_upload_returns_500_when_storing_embeddings_fails(client, monkeypatch):
    monkeypatch.setattr(ingestion, "ingest_pdf", lambda data, name: [Document(page_content="x")])

    def boom(chunks):
        raise RuntimeError("SSL connection has been closed unexpectedly")
    monkeypatch.setattr(vectorstore, "add_documents", boom)

    response = client.post(
        "/documents/upload",
        files={"file": ("test.pdf", b"%PDF-1.4", "application/pdf")}
    )

    assert response.status_code == 500
    assert "SSL connection" in response.json()["detail"]


def test_ingest_web_page_success(client, monkeypatch):
    fake_chunks = [Document(page_content="scraped page text")]
    monkeypatch.setattr(ingestion, "ingest_web", lambda url: fake_chunks)
    monkeypatch.setattr(vectorstore, "add_documents", lambda chunks: None)

    response = client.post("/documents/web", json={"url": "https://example.com/docs"})

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "https://example.com/docs"
    assert body["source_type"] == "web"
    assert body["chunk_count"] == 1


def test_ingest_web_page_rejects_an_invalid_url(client):
    response = client.post("/documents/web", json={"url": "not-a-url"})

    assert response.status_code == 422


def test_ingest_web_page_returns_422_when_the_page_has_no_content(client, monkeypatch):
    def fail(url):
        raise ValueError(f"No content found at '{url}'.")
    monkeypatch.setattr(ingestion, "ingest_web", fail)

    response = client.post("/documents/web", json={"url": "https://example.com/empty"})

    assert response.status_code == 422


def test_delete_document_by_name_success(client, monkeypatch):
    monkeypatch.setattr(
        vectorstore, "delete_by_source",
        lambda source_name: {"deleted_count": 3, "collection_id": "abc-123"}
    )

    response = client.delete("/documents/report.pdf")

    assert response.status_code == 200
    body = response.json()
    assert body["collection_id"] == "abc-123"
    assert "3 vector chunk" in body["detail"]


def test_delete_document_by_name_returns_404_when_nothing_matches(client, monkeypatch):
    monkeypatch.setattr(
        vectorstore, "delete_by_source",
        lambda source_name: {"deleted_count": 0, "collection_id": None}
    )

    response = client.delete("/documents/missing.pdf")

    assert response.status_code == 404


def test_delete_document_by_name_accepts_a_url_encoded_web_source(client, monkeypatch):
    captured = {}

    def fake_delete(source_name):
        captured["source_name"] = source_name
        return {"deleted_count": 1, "collection_id": "abc"}
    monkeypatch.setattr(vectorstore, "delete_by_source", fake_delete)

    response = client.delete("/documents/https%3A%2F%2Ffastapi.tiangolo.com")

    assert response.status_code == 200
    assert captured["source_name"] == "https://fastapi.tiangolo.com"
