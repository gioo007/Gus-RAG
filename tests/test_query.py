import uuid
from unittest.mock import MagicMock

from langchain_core.documents import Document

from app.services import generation, retrieval, chat_history


class FakeHistory:
    def __init__(self, messages=None):
        self.messages = messages or []
        self.added_user = []
        self.added_ai = []

    def add_user_message(self, message):
        self.added_user.append(message)

    def add_ai_message(self, message):
        self.added_ai.append(message)


def _patch_history(monkeypatch, fake_history):
    def fake_get_history(session_id):
        class _Ctx:
            def __enter__(self):
                return fake_history

            def __exit__(self, exc_type, exc, tb):
                return False

        return _Ctx()

    monkeypatch.setattr(chat_history, "get_history", fake_get_history)


def test_query_returns_the_answer_and_deduped_sources_in_relevance_order(client, monkeypatch):
    fake_history = FakeHistory()
    _patch_history(monkeypatch, fake_history)
    chunks = [
        Document(page_content="a", metadata={"source": "a.pdf", "source_type": "pdf"}),
        Document(page_content="b", metadata={"source": "a.pdf", "source_type": "pdf"}),
        Document(page_content="c", metadata={"source": "https://example.com", "source_type": "web"}),
    ]
    monkeypatch.setattr(retrieval, "retrieve", lambda question, version, session_id=None: chunks)
    monkeypatch.setattr(
        generation,
        "generate",
        lambda question, chunks, history: "the answer",
    )

    response = client.post("/query", json={"question": "what is this about?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "the answer"
    assert [s["source"] for s in body["sources"]] == ["a.pdf", "https://example.com"]
    assert fake_history.added_user == ["what is this about?"]
    assert fake_history.added_ai == ["the answer"]
    uuid.UUID(body["session_id"])  # a session id was generated since none was passed


def test_query_reuses_the_provided_session_id(client, monkeypatch):
    _patch_history(monkeypatch, FakeHistory())
    monkeypatch.setattr(retrieval, "retrieve", lambda question, version, session_id=None: [])
    monkeypatch.setattr(generation, "generate", lambda question, chunks, history: "answer")

    response = client.post("/query", json={"question": "q", "session_id": "my-session"})

    assert response.json()["session_id"] == "my-session"


def test_query_passes_only_the_last_thirty_history_messages_to_generation(client, monkeypatch):
    fake_history = FakeHistory(messages=list(range(40)))
    _patch_history(monkeypatch, fake_history)
    monkeypatch.setattr(retrieval, "retrieve", lambda question, version, session_id=None: [])
    captured = {}

    def fake_generate(question, chunks=None, history=None):
        captured["history"] = history
        return "answer"

    monkeypatch.setattr(generation, "generate", fake_generate)

    client.post("/query", json={"question": "q"})

    assert captured["history"] == list(range(10, 40))


def test_query_returns_500_when_retrieval_fails(client, monkeypatch):
    _patch_history(monkeypatch, FakeHistory())

    def boom(question, version, session_id=None):
        raise RuntimeError("pgvector is down")

    monkeypatch.setattr(retrieval, "retrieve", boom)

    response = client.post("/query", json={"question": "q"})

    assert response.status_code == 500
    assert "pgvector is down" in response.json()["detail"]


def test_query_returns_500_when_generation_fails(client, monkeypatch):
    _patch_history(monkeypatch, FakeHistory())
    monkeypatch.setattr(retrieval, "retrieve", lambda question, version, session_id=None: [])

    def boom(question, chunks=None, history=None):
        raise RuntimeError("groq rate limited")

    monkeypatch.setattr(generation, "generate", boom)

    response = client.post("/query", json={"question": "q"})

    assert response.status_code == 500
    assert "groq rate limited" in response.json()["detail"]


def test_query_defaults_version_to_v1(client, monkeypatch):
    _patch_history(monkeypatch, FakeHistory())
    captured = {}

    def fake_retrieve(question, version, session_id=None):
        captured["version"] = version
        return []

    monkeypatch.setattr(retrieval, "retrieve", fake_retrieve)
    monkeypatch.setattr(generation, "generate", lambda question, chunks, history: "answer")

    client.post("/query", json={"question": "q"})

    assert captured["version"] == "v1"


def test_query_v2_uses_run_agent_and_returns_its_sources(client, monkeypatch):
    fake_history = FakeHistory()
    _patch_history(monkeypatch, fake_history)

    result = {
        "answer": "the answer",
        "sources": [
            {"source": "a.pdf", "source_type": "pdf"},
            {"source": "https://example.com", "source_type": "web"},
        ],
    }
    mock_run_agent = MagicMock(return_value=result)

    monkeypatch.setattr(generation, "run_agent", mock_run_agent)

    response = client.post(
        "/query",
        json={
            "question": "what is this about?",
            "version": "v2",
            "session_id": "sess-42",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "the answer"
    assert [s["source"] for s in body["sources"]] == ["a.pdf", "https://example.com"]
    assert fake_history.added_user == ["what is this about?"]
    assert fake_history.added_ai == ["the answer"]
    mock_run_agent.assert_called_once_with(
        "what is this about?",
        [],
        session_id="sess-42",
    )


def test_query_v2_passes_the_last_thirty_history_messages_and_a_generated_session_id(client, monkeypatch):
    _patch_history(monkeypatch, FakeHistory(messages=list(range(40))))
    mock_run_agent = MagicMock(return_value={"answer": "answer", "sources": []})
    monkeypatch.setattr(generation, "run_agent", mock_run_agent)

    response = client.post("/query", json={"question": "q", "version": "v2"})

    body = response.json()
    uuid.UUID(body["session_id"])
    mock_run_agent.assert_called_once_with(
        "q", list(range(10, 40)), session_id=body["session_id"]
    )


def test_query_v2_leaves_retrieval_to_the_agent(client, monkeypatch):
    _patch_history(monkeypatch, FakeHistory())
    mock_retrieve = MagicMock()
    monkeypatch.setattr(retrieval, "retrieve", mock_retrieve)
    monkeypatch.setattr(
        generation, "run_agent", MagicMock(return_value={"answer": "answer", "sources": []})
    )

    client.post("/query", json={"question": "q", "version": "v2"})

    mock_retrieve.assert_not_called()


def test_query_v2_returns_500_and_saves_nothing_when_the_agent_fails(client, monkeypatch):
    fake_history = FakeHistory()
    _patch_history(monkeypatch, fake_history)

    def boom(question, history, session_id):
        raise RuntimeError("groq rate limited")

    monkeypatch.setattr(generation, "run_agent", boom)

    response = client.post("/query", json={"question": "q", "version": "v2"})

    assert response.status_code == 500
    assert "groq rate limited" in response.json()["detail"]
    assert fake_history.added_user == []
    assert fake_history.added_ai == []


def test_query_v1_saves_nothing_to_history_when_generation_fails(client, monkeypatch):
    fake_history = FakeHistory()
    _patch_history(monkeypatch, fake_history)
    monkeypatch.setattr(retrieval, "retrieve", lambda question, version, session_id=None: [])

    def boom(question, chunks=None, history=None):
        raise RuntimeError("groq rate limited")

    monkeypatch.setattr(generation, "generate", boom)

    client.post("/query", json={"question": "q"})

    assert fake_history.added_user == []
    assert fake_history.added_ai == []