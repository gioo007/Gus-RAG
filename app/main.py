from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import documents, query

app = FastAPI(
    title="RAG Capstone API",
    description="Document ingestion + retrieval-augmented generation over your own docs."
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the RAG Capstone API"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(query.router, prefix="/query", tags=["query"])

@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}