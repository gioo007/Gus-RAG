from unittest.mock import MagicMock

from langchain_core.documents import Document

from app.services import vectorstore


def test_psycopg_connection_string_passes_through_an_already_correct_url():
    url = "postgresql+psycopg://user:pass@host/db"
    assert vectorstore.psycopg_connection_string(url) == url


def test_psycopg_connection_string_upgrades_a_plain_postgresql_url():
    url = "postgresql://user:pass@host/db"
    assert vectorstore.psycopg_connection_string(url) == "postgresql+psycopg://user:pass@host/db"


def test_psycopg_connection_string_leaves_an_unrecognized_scheme_untouched():
    url = "sqlite:///local.db"
    assert vectorstore.psycopg_connection_string(url) == url


def test_add_documents_with_no_chunks_skips_the_store_call(monkeypatch):
    mock_store = MagicMock()
    monkeypatch.setattr(vectorstore, "vector_store", mock_store)

    result = vectorstore.add_documents([])

    assert result == []
    mock_store.add_documents.assert_not_called()


def test_add_documents_delegates_to_the_vector_store(monkeypatch):
    fake_chunks = [
        Document(page_content="chunk-1"),
        Document(page_content="chunk-2"),
    ]
    mock_store = MagicMock()
    mock_store.add_documents.return_value = ["id-1", "id-2"]
    monkeypatch.setattr(vectorstore, "vector_store", mock_store)

    result = vectorstore.add_documents(fake_chunks)

    mock_store.add_documents.assert_called_once_with(fake_chunks)
    assert result == ["id-1", "id-2"]


def _connection_from(context_manager_mock):
    return context_manager_mock.__enter__.return_value


def test_ensure_indexes_creates_the_composite_index(monkeypatch):
    mock_engine = MagicMock()
    monkeypatch.setattr(vectorstore, "engine", mock_engine)

    vectorstore.ensure_indexes()

    conn = _connection_from(mock_engine.begin.return_value)
    executed_sql = str(conn.execute.call_args[0][0])
    assert "CREATE INDEX IF NOT EXISTS idx_embedding_collection_source" in executed_sql
    assert "cmetadata ->> 'source'" in executed_sql


def test_delete_by_source_returns_deleted_count_and_collection_id(monkeypatch):
    mock_engine = MagicMock()
    conn = _connection_from(mock_engine.begin.return_value)
    fake_collection_id = "11111111-1111-1111-1111-111111111111"
    conn.execute.return_value.fetchall.return_value = [(fake_collection_id,)]
    monkeypatch.setattr(vectorstore, "engine", mock_engine)

    result = vectorstore.delete_by_source("q3_report.pdf")

    args = conn.execute.call_args[0]
    assert args[1] == {"collection_name": vectorstore.COLLECTION_NAME, "source_name": "q3_report.pdf"}
    assert result == {"deleted_count": 1, "collection_id": fake_collection_id}


def test_delete_by_source_returns_zero_and_none_when_nothing_matches(monkeypatch):
    mock_engine = MagicMock()
    conn = _connection_from(mock_engine.begin.return_value)
    conn.execute.return_value.fetchall.return_value = []
    monkeypatch.setattr(vectorstore, "engine", mock_engine)

    result = vectorstore.delete_by_source("missing.pdf")

    assert result == {"deleted_count": 0, "collection_id": None}


def test_list_documents_returns_rows_as_plain_dicts(monkeypatch):
    mock_engine = MagicMock()
    conn = _connection_from(mock_engine.connect.return_value)
    fake_row = {"source": "a.pdf", "source_type": "pdf", "chunk_count": 3}
    conn.execute.return_value.mappings.return_value.all.return_value = [fake_row]
    monkeypatch.setattr(vectorstore, "engine", mock_engine)

    result = vectorstore.list_documents()

    assert result == [fake_row]
    args = conn.execute.call_args[0]
    assert args[1] == {"collection_name": vectorstore.COLLECTION_NAME}
