from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.services import generation


class ScriptedChatModel(BaseChatModel):
    """Fake chat model that replays a fixed list of AIMessages, one per model call."""

    script: list = []
    calls: int = 0

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        message = self.script[min(self.calls, len(self.script) - 1)]
        self.calls += 1
        return ChatResult(generations=[ChatGeneration(message=message)])


def _tool_call(call_id, question, name="retrieve_documents"):
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": {"question": question}, "id": call_id}],
    )


def _runtime(session_id):
    return SimpleNamespace(context=generation.AgentContext(session_id=session_id))


@pytest.fixture
def fresh_agent_cache():
    generation.get_agent.cache_clear()
    yield
    generation.get_agent.cache_clear()


def test_generate_stuffs_chunks_into_the_system_prompt_and_returns_the_answer(monkeypatch):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = SimpleNamespace(content="Paris.")
    monkeypatch.setattr(generation, "llm", mock_llm)
    chunks = [
        Document(page_content="Paris is the capital of France."),
        Document(page_content="The Eiffel Tower was completed in 1889."),
    ]

    answer = generation.generate("What is the capital of France?", chunks)

    assert answer == "Paris."
    messages = mock_llm.invoke.call_args[0][0]
    assert "Paris is the capital of France." in messages[0].content
    assert "The Eiffel Tower was completed in 1889." in messages[0].content
    assert messages[-1].content == "What is the capital of France?"


def test_generate_places_history_between_the_system_prompt_and_the_question(monkeypatch):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = SimpleNamespace(content="ok")
    monkeypatch.setattr(generation, "llm", mock_llm)
    history = [HumanMessage(content="hi"), AIMessage(content="hello")]

    generation.generate("follow up question", [], history)

    messages = mock_llm.invoke.call_args[0][0]
    assert messages[1] is history[0]
    assert messages[2] is history[1]
    assert messages[-1].content == "follow up question"


def test_generate_coerces_non_string_content_to_a_string(monkeypatch):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = SimpleNamespace(content=123)
    monkeypatch.setattr(generation, "llm", mock_llm)

    answer = generation.generate("q", [])

    assert answer == "123"


def test_run_agent_uses_session_context_and_returns_deduped_sources(monkeypatch):
    question = "What is the capital of France?"
    history = [HumanMessage(content="Tell me about France.")]
    documents = [
        Document(
            page_content="Paris is the capital of France.",
            metadata={"source": "wiki.pdf", "source_type": "pdf"},
        ),
        Document(
            page_content="Paris is the capital of France.",
            metadata={"source": "wiki.pdf", "source_type": "pdf"},
        ),
    ]
    tool_message = ToolMessage(
        content="Paris is the capital of France.",
        tool_call_id="call_123",
        artifact=documents,
    )
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = {
        "messages": [*history, HumanMessage(content=question), tool_message, AIMessage(content="Paris.")]
    }
    monkeypatch.setattr(generation, "get_agent", lambda: mock_agent)

    result = generation.run_agent(question, history, session_id="sess-1")

    assert result["answer"] == "Paris."
    assert result["sources"] == [{"source": "wiki.pdf", "source_type": "pdf"}]
    invoke_args, invoke_kwargs = mock_agent.invoke.call_args
    assert invoke_args[0]["messages"] == [*history, HumanMessage(content=question)]
    assert invoke_kwargs["context"] == generation.AgentContext(session_id="sess-1")


def test_run_agent_returns_no_sources_when_the_agent_never_retrieves(monkeypatch):
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = {
        "messages": [HumanMessage(content="hi"), AIMessage(content="Hello, I am Gus.")]
    }
    monkeypatch.setattr(generation, "get_agent", lambda: mock_agent)

    result = generation.run_agent("hi", [], session_id="sess-1")

    assert result == {"answer": "Hello, I am Gus.", "sources": []}


def test_run_agent_ignores_tool_messages_that_came_from_the_input_history(monkeypatch):
    old_doc = Document(page_content="old", metadata={"source": "old.pdf"})
    new_doc = Document(page_content="new", metadata={"source": "new.pdf"})
    history = [ToolMessage(content="old", tool_call_id="old-call", artifact=[old_doc])]
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = {
        "messages": [
            *history,
            HumanMessage(content="q"),
            ToolMessage(content="new", tool_call_id="new-call", artifact=[new_doc]),
            AIMessage(content="answer"),
        ]
    }
    monkeypatch.setattr(generation, "get_agent", lambda: mock_agent)

    result = generation.run_agent("q", history, session_id="sess-1")

    assert [s["source"] for s in result["sources"]] == ["new.pdf"]


def test_retrieve_documents_schema_hides_session_id_from_the_model():
    props = generation.retrieve_documents.tool_call_schema.model_json_schema()["properties"]

    assert set(props) == {"question"}


def test_retrieve_documents_scopes_retrieval_to_the_context_session(monkeypatch):
    captured = {}
    docs = [Document(page_content="Paris is the capital.", metadata={"source": "wiki.pdf"})]

    def fake_retrieve(question, version, session_id=None):
        captured.update(question=question, version=version, session_id=session_id)
        return docs

    monkeypatch.setattr(generation.retrieval, "retrieve", fake_retrieve)

    content, artifact = generation.retrieve_documents.func(
        question="capital of France?", runtime=_runtime("sess-1")
    )

    assert captured == {"question": "capital of France?", "version": "v2", "session_id": "sess-1"}
    assert "Paris is the capital." in content
    assert "wiki.pdf" in content
    assert artifact == docs


def test_retrieve_documents_reports_when_nothing_was_found(monkeypatch):
    monkeypatch.setattr(generation.retrieval, "retrieve", lambda question, version, session_id=None: [])

    content, artifact = generation.retrieve_documents.func(question="q", runtime=_runtime("sess-1"))

    assert content == "No relevant passages found."
    assert artifact == []


def test_retrieve_documents_fails_closed_without_a_session_id(monkeypatch):
    retrieve = MagicMock()
    monkeypatch.setattr(generation.retrieval, "retrieve", retrieve)

    with pytest.raises(ValueError):
        generation.retrieve_documents.func(question="q", runtime=_runtime(""))

    retrieve.assert_not_called()


def test_get_agent_is_built_once_with_the_expected_configuration(monkeypatch, fresh_agent_cache):
    mock_create_agent = MagicMock(return_value="the-agent")
    monkeypatch.setattr(generation, "create_agent", mock_create_agent)

    first = generation.get_agent()
    second = generation.get_agent()

    assert first == second == "the-agent"
    mock_create_agent.assert_called_once()
    kwargs = mock_create_agent.call_args.kwargs
    assert kwargs["model"] is generation.llm
    assert kwargs["tools"] == [generation.retrieve_documents]
    assert kwargs["system_prompt"] == generation.AGENT_PROMPT
    assert kwargs["context_schema"] is generation.AgentContext
    assert len(kwargs["middleware"]) == 1


def test_agent_scopes_every_retrieval_to_the_session_and_caps_the_number_of_calls(
    monkeypatch, fresh_agent_cache
):
    sessions = []

    def fake_retrieve(question, version, session_id=None):
        sessions.append(session_id)
        return [
            Document(
                page_content=f"passage for {question}",
                metadata={"source": f"doc{len(sessions)}.pdf", "source_type": "pdf"},
            )
        ]

    monkeypatch.setattr(generation.retrieval, "retrieve", fake_retrieve)
    # The model keeps asking to retrieve (5 times) before it finally answers.
    model = ScriptedChatModel(
        script=[_tool_call(f"c{i}", f"q{i}") for i in range(5)] + [AIMessage(content="final answer")]
    )
    monkeypatch.setattr(generation, "llm", model)

    result = generation.run_agent("what?", [], session_id="sess-9")

    assert result["answer"] == "final answer"
    assert sessions == ["sess-9"] * generation.MAX_RETRIEVALS
    assert [s["source"] for s in result["sources"]] == ["doc1.pdf", "doc2.pdf", "doc3.pdf"]


def test_agent_survives_a_call_to_an_unknown_tool(monkeypatch, fresh_agent_cache):
    retrieve = MagicMock()
    monkeypatch.setattr(generation.retrieval, "retrieve", retrieve)
    model = ScriptedChatModel(
        script=[_tool_call("c1", "q", name="does_not_exist"), AIMessage(content="recovered")]
    )
    monkeypatch.setattr(generation, "llm", model)

    result = generation.run_agent("q", [], session_id="sess-1")

    assert result == {"answer": "recovered", "sources": []}
    retrieve.assert_not_called()