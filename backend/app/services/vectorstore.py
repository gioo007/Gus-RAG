from langchain_core.documents import Document
from langchain_voyageai import VoyageAIEmbeddings
from langchain_postgres import PGVector
from pydantic import SecretStr
from sqlalchemy import create_engine, text
from app.core.config import settings


COLLECTION_NAME = "documents"

def psycopg_connection_string(database_url: str) -> str:
    #normalize db url
    if database_url.startswith("postgresql+psycopg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url

engine = create_engine(
    psycopg_connection_string(settings.DATABASE_URL),
    pool_pre_ping=True,
    pool_recycle=300,
)

embeddings = VoyageAIEmbeddings(
    model=settings.VOYAGE_MODEL, 
    api_key=SecretStr(settings.VOYAGE_API_KEY)
)

vector_store = PGVector(
    embeddings=embeddings,
    collection_name=COLLECTION_NAME,
    connection=engine,
    use_jsonb=True,
    create_extension=False,  #toggle to True if you want to create the pgvector extension automatically (requires superuser privileges)
)


def add_documents(chunks: list[Document]) -> list[str]:
    #returns generated row ids
    if not chunks:
        return []

    ids: list[str] = []
    batch_size = settings.INGESTION_BATCH_SIZE
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        ids.extend(vector_store.add_documents(batch))

    return ids


def ensure_indexes() -> None:

    source_index = text(
        """
        CREATE INDEX IF NOT EXISTS idx_embedding_collection_source
        ON langchain_pg_embedding (collection_id, (cmetadata ->> 'source'))
        """
    )
    session_index = text(
        """
        CREATE INDEX IF NOT EXISTS idx_embedding_collection_session
        ON langchain_pg_embedding (collection_id, (cmetadata ->> 'session_id'))
        """
    )
    with engine.begin() as conn:
        conn.execute(source_index)
        conn.execute(session_index)
 
ensure_indexes()
 
 
def delete_by_source(source_name: str, session_id: str | None = None) -> dict:
    params: dict[str, str] = {"collection_name": COLLECTION_NAME, "source_name": source_name}
    clauses = [
        "e.collection_id = c.uuid",
        "c.name = :collection_name",
        "e.cmetadata ->> 'source' = :source_name",
    ]
    if session_id is not None:
        clauses.append("e.cmetadata ->> 'session_id' = :session_id")
        params["session_id"] = session_id

    query = text(
        f"""
        DELETE FROM langchain_pg_embedding e
        USING langchain_pg_collection c
        WHERE {' AND '.join(clauses)}
        RETURNING e.collection_id
        """
    )
    with engine.begin() as conn:
        rows = conn.execute(query, params).fetchall()
 
    return {
        "deleted_count": len(rows),
        "collection_id": str(rows[0][0]) if rows else None
    }

 
def list_documents(session_id: str | None = None) -> list[dict]:
    params: dict[str, str] = {"collection_name": COLLECTION_NAME}
    filters = ["c.name = :collection_name"]
    if session_id is not None:
        filters.append("e.cmetadata ->> 'session_id' = :session_id")
        params["session_id"] = session_id

    #query embeddings to get the chunk counts (if we just query the collection table, we won't know how many chunks are associated with each source)
    query = text(
        f"""
        SELECT
            e.cmetadata ->> 'source' AS source,
            e.cmetadata ->> 'source_type' AS source_type,
            e.cmetadata ->> 'session_id' AS session_id,
            COUNT(*) AS chunk_count
        FROM langchain_pg_embedding e
        JOIN langchain_pg_collection c ON e.collection_id = c.uuid
        WHERE {' AND '.join(filters)}
        GROUP BY source, source_type, session_id
        ORDER BY source
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(query, params).mappings().all()
    return [dict(row) for row in rows]


def get_all_documents(session_id: str | None = None) -> list[Document]:
    #if the doc count grows into the thousands, this should move to a cached/paginated read instead of a full scan.
    params: dict[str, str] = {"collection_name": COLLECTION_NAME}
    filters = ["c.name = :collection_name"]
    if session_id is not None:
        filters.append("e.cmetadata ->> 'session_id' = :session_id")
        params["session_id"] = session_id

    query = text(
        f"""
        SELECT e.document AS content, e.cmetadata AS metadata
        FROM langchain_pg_embedding e
        JOIN langchain_pg_collection c ON e.collection_id = c.uuid
        WHERE {' AND '.join(filters)}
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(query, params).mappings().all()
    return [
        Document(page_content=row["content"], metadata=dict(row["metadata"] or {}))
        for row in rows
    ]