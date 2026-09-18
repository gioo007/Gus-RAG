import psycopg
from langchain_postgres import PostgresChatMessageHistory
import contextlib

from app.core.config import settings

TABLE_NAME = "chat_history"

setup_connection = psycopg.connect(settings.DATABASE_URL, autocommit=True)
PostgresChatMessageHistory.create_tables(setup_connection, TABLE_NAME)
setup_connection.close()


@contextlib.contextmanager
def get_history(session_id: str):
    connection = psycopg.connect(settings.DATABASE_URL, autocommit=True)
    try:
        yield PostgresChatMessageHistory(TABLE_NAME, session_id, sync_connection=connection)
    finally:
        connection.close()