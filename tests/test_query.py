import uuid
from fastapi import HTTPException
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
    monkeypatch.setattr(generation, "generate", lambda question, chunks, history, version="v1", session_id=None: "the answer")

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
    monkeypatch.setattr(generation, "generate", lambda question, chunks, history, version="v1", session_id=None: "answer")

    response = client.post("/query", json={"question": "q", "session_id": "my-session"})

    assert response.json()["session_id"] == "my-session"


def test_query_passes_only_the_last_thirty_history_messages_to_generation(client, monkeypatch):
    fake_history = FakeHistory(messages=list(range(40)))
    _patch_history(monkeypatch, fake_history)
    monkeypatch.setattr(retrieval, "retrieve", lambda question, version, session_id=None: [])
    captured = {}

    def fake_generate(question, chunks, history, version="v1", session_id=None):
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

    def boom(question, chunks, history, version="v1", session_id=None):
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
    monkeypatch.setattr(generation, "generate", lambda question, chunks, history, version="v1", session_id=None: "answer")

    client.post("/query", json={"question": "q"})

    assert captured["version"] == "v1"


def test_query_v2_uses_the_tool_calling_agent(client, monkeypatch):
    fake_history = FakeHistory()
    _patch_history(monkeypatch, fake_history)

    def fake_run_agent(question, history, session_id=None):
        assert session_id == "sess-42"
        assert question == "what is this about?"
        return {
            "answer": "the answer",
            "sources": [
                {"source": "a.pdf", "source_type": "pdf"},
                {"source": "https://example.com", "source_type": "web"},
                {"source": "a.pdf", "source_type": "pdf"},
            ],
        }

    monkeypatch.setattr(generation, "run_agent", fake_run_agent)

    response = client.post("/query", json={"question": "what is this about?", "version": "v2", "session_id": "sess-42"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "the answer"
    assert [s["source"] for s in body["sources"]] == ["a.pdf", "https://example.com"]
    assert fake_history.added_user == ["what is this about?"]
    assert fake_history.added_ai == ["the answer"]
