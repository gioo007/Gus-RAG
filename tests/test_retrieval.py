from unittest.mock import MagicMock

from app.services import retrieval


def test_retrieve_uses_the_default_k_and_returns_the_retrievers_result(monkeypatch):
    fake_retriever = MagicMock()
    fake_retriever.invoke.return_value = ["doc-1"]
    mock_vector_store = MagicMock()
    mock_vector_store.as_retriever.return_value = fake_retriever
    monkeypatch.setattr(retrieval, "vector_store", mock_vector_store)

    result = retrieval.retrieve("some question")

    mock_vector_store.as_retriever.assert_called_once_with(search_kwargs={"k": retrieval.DEFAULT_K})
    fake_retriever.invoke.assert_called_once_with("some question")
    assert result == ["doc-1"]


def test_retrieve_passes_through_a_custom_k(monkeypatch):
    fake_retriever = MagicMock()
    mock_vector_store = MagicMock()
    mock_vector_store.as_retriever.return_value = fake_retriever
    monkeypatch.setattr(retrieval, "vector_store", mock_vector_store)

    retrieval.retrieve("q", k=9)

    mock_vector_store.as_retriever.assert_called_once_with(search_kwargs={"k": 9})
