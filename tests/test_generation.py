from types import SimpleNamespace
from unittest.mock import MagicMock

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage

from app.services import generation


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


def test_run_agent_executes_retrieval_tool_and_returns_answer_and_sources(monkeypatch):
    mock_llm = MagicMock()
    mock_model = MagicMock()
    mock_model.invoke.side_effect = [
        SimpleNamespace(tool_calls=[{
            "id": "call_123",
            "name": "retrieve_documents",
            "args": {"question": "What is the capital of France?", "session_id": "sess-1"},
        }], content=""),
        SimpleNamespace(content="Paris."),
    ]
    mock_llm.bind_tools.return_value = mock_model
    monkeypatch.setattr(generation, "llm", mock_llm)
    monkeypatch.setattr(
        generation.retrieval,
        "retrieve",
        lambda question, version, session_id=None: [
            Document(
                page_content="Paris is the capital of France.",
                metadata={"source": "wiki.pdf", "source_type": "pdf"},
            ),
            Document(
                page_content="Paris is the capital of France.",
                metadata={"source": "wiki.pdf", "source_type": "pdf"},
            ),
        ],
    )

    result = generation.run_agent("What is the capital of France?", history=[], session_id="sess-1")

    assert result["answer"] == "Paris."
    assert result["sources"] == [{"source": "wiki.pdf", "source_type": "pdf"}]
    assert mock_llm.bind_tools.call_count == 1
    assert mock_model.invoke.call_count == 2
