from unittest.mock import MagicMock

import pytest

from app.services import chat_history


def test_get_history_opens_a_connection_builds_the_history_and_closes_on_success(monkeypatch):
    mock_connection = MagicMock()
    mock_connect = MagicMock(return_value=mock_connection)
    monkeypatch.setattr(chat_history.psycopg, "connect", mock_connect)
    mock_history_cls = MagicMock()
    monkeypatch.setattr(chat_history, "PostgresChatMessageHistory", mock_history_cls)

    with chat_history.get_history("session-1") as history:
        assert history is mock_history_cls.return_value

    mock_connect.assert_called_once_with(chat_history.settings.DATABASE_URL, autocommit=True)
    mock_history_cls.assert_called_once_with(chat_history.TABLE_NAME, "session-1", sync_connection=mock_connection)
    mock_connection.close.assert_called_once()


def test_get_history_still_closes_the_connection_if_the_caller_raises(monkeypatch):
    mock_connection = MagicMock()
    mock_connect = MagicMock(return_value=mock_connection)
    monkeypatch.setattr(chat_history.psycopg, "connect", mock_connect)
    monkeypatch.setattr(chat_history, "PostgresChatMessageHistory", MagicMock())

    with pytest.raises(ValueError):
        with chat_history.get_history("session-2"):
            raise ValueError("boom")

    mock_connection.close.assert_called_once()
