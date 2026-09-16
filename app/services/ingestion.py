import os
import tempfile
import zipfile
from pathlib import Path
from langchain_community.document_loaders import (
    Docx2txtLoader,
    NotionDirectoryLoader,
    PyPDFLoader,
    WebBaseLoader
)
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200

splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP
)


def chunk_documents(docs: list[Document]) -> list[Document]: 
    return splitter.split_documents(docs)


def ingest_pdf(file_bytes: bytes, filename: str) -> list[Document]:
    #temp file deleted after PyPDFLoader loads it
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp_path = tmp.name
    try:
        tmp.write(file_bytes)
        tmp.close()
        
        docs = PyPDFLoader(tmp_path).load()
    finally:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except PermissionError:
                pass

    if not docs:
        raise ValueError(f"No extractable text found in '{filename}'.")

    #PyPDFLoader overwrites the metadata with the file path, so we restore the original filename
    for doc in docs:
        doc.metadata["source"] = filename

    return chunk_documents(docs)


def ingest_docx(file_bytes: bytes, filename: str) -> list[Document]:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    tmp_path = tmp.name
    try:
        tmp.write(file_bytes)
        tmp.close()
        
        docs = Docx2txtLoader(tmp_path).load()
    finally:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except PermissionError:
                pass

    if not docs:
        raise ValueError(f"No extractable text found in '{filename}'.")
 
    for doc in docs:
        doc.metadata["source"] = filename
 
    return chunk_documents(docs)


def ingest_web(url: str) -> list[Document]:
    try:
        docs = WebBaseLoader(url).load()
    except Exception as e:
        raise ValueError(f"Could not load content from '{url}': {e}") from e

    if not docs:
        raise ValueError(f"No content found at '{url}'.")

    return chunk_documents(docs)


def ingest_notion(zip_bytes: bytes) -> list[Document]:
    #load an unzipped Notion Markdown export and return chunked Documents.
    with tempfile.TemporaryDirectory() as tmp_dir:
        zip_path = Path(tmp_dir) / "export.zip"
        zip_path.write_bytes(zip_bytes)

        extract_dir = Path(tmp_dir) / "notion_export"
        try:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(extract_dir)
        except zipfile.BadZipFile as e:
            raise ValueError("Uploaded file is not a valid .zip archive.") from e

        docs = NotionDirectoryLoader(str(extract_dir)).load()

        if not docs:
            raise ValueError("No Markdown files found in the Notion export.")

        return chunk_documents(docs)