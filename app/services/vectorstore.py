from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector
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


embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    encode_kwargs={"normalize_embeddings": True},
)

vector_store = PGVector(
    embeddings=embeddings,
    collection_name=COLLECTION_NAME,
    connection=psycopg_connection_string(settings.DATABASE_URL),
    use_jsonb=True,
    create_extension=False,  #toggle to True if you want to create the pgvector extension automatically (requires superuser privileges)
)


def add_documents(chunks: list[Document]) -> list[str]:
    #returns generated row ids
    if not chunks:
        return []
    return vector_store.add_documents(chunks)


engine = create_engine(psycopg_connection_string(settings.DATABASE_URL))

def ensure_indexes() -> None:

    query = text(
        """
        CREATE INDEX IF NOT EXISTS idx_embedding_collection_source
        ON langchain_pg_embedding (collection_id, (cmetadata ->> 'source'))
        """
    )
    with engine.begin() as conn:
        conn.execute(query)
 
ensure_indexes()
 
 
def delete_by_source(source_name: str) -> dict:

    query = text(
        """
        DELETE FROM langchain_pg_embedding e
        USING langchain_pg_collection c
        WHERE e.collection_id = c.uuid
          AND c.name = :collection_name
          AND e.cmetadata ->> 'source' = :source_name
        RETURNING e.collection_id
        """
    )
    with engine.begin() as conn:
        rows = conn.execute(query, {"collection_name": COLLECTION_NAME, "source_name": source_name}).fetchall()
 
    return {
        "deleted_count": len(rows),
        "collection_id": str(rows[0][0]) if rows else None
    }

 
def list_documents() -> list[dict]:

    #query embeddings to get the chunk counts (if we just query the collection table, we won't know how many chunks are associated with each source)
    query = text(
        """
        SELECT
            e.cmetadata ->> 'source' AS source,
            e.cmetadata ->> 'source_type' AS source_type,
            COUNT(*) AS chunk_count
        FROM langchain_pg_embedding e
        JOIN langchain_pg_collection c ON e.collection_id = c.uuid
        WHERE c.name = :collection_name
        GROUP BY source, source_type
        ORDER BY source
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(query, {"collection_name": COLLECTION_NAME}).mappings().all()
    return [dict(row) for row in rows]