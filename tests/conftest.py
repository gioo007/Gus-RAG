import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# langchain_huggingface pulls in sentence-transformers + torch (multi-GB).
# The real thing is never touched by this suite (embeddings are always
# mocked out below), so it's stubbed here rather than required as a test
# dependency. Production code still needs the real package in
# requirements.txt; only this test environment gets a stand-in, which
# keeps `pip install` + `pytest` fast in CI.
if "langchain_huggingface" not in sys.modules:
    _fake_hf_module = types.ModuleType("langchain_huggingface")
    setattr(_fake_hf_module, "HuggingFaceEmbeddings", object)  # overwritten by patch() below
    sys.modules["langchain_huggingface"] = _fake_hf_module

patch("sqlalchemy.create_engine", return_value=MagicMock(name="engine")).start()
patch("langchain_huggingface.HuggingFaceEmbeddings", return_value=MagicMock(name="embeddings")).start()
patch("langchain_postgres.PGVector", return_value=MagicMock(name="vector_store")).start()
patch("psycopg.connect", return_value=MagicMock(name="psycopg_connection")).start()
patch("langchain_postgres.PostgresChatMessageHistory.create_tables").start()
patch("langchain_groq.ChatGroq", return_value=MagicMock(name="llm")).start()

# engine, embeddings, vector_store, and llm
# are all mocks, and no service module will try to reach a real DB, model, or API at import time.
from backend.app.main import app

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def client():
    #a TestClient wired to the real app, with all external services mocked
    return TestClient(app)


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    return (FIXTURES_DIR / "sample.pdf").read_bytes()


@pytest.fixture
def sample_docx_bytes() -> bytes:
    return (FIXTURES_DIR / "sample.docx").read_bytes()


@pytest.fixture
def sample_notion_zip_bytes() -> bytes:
    return (FIXTURES_DIR / "sample_notion_export.zip").read_bytes()
