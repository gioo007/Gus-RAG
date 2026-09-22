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
