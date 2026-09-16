# RAG Capstone API

A retrieval-augmented generation (RAG) API built with **FastAPI** and **LangChain**, answering questions over user-uploaded documents. Embeddings are stored in **pgvector** on a hosted **Neon Postgres** instance, with generation running on **Groq**. This is the capstone project bridging the DeepLearning.AI LangChain short courses ("LLM Application Development" and "Chat With Your Data") into a deployable, production-shaped stack.

> **Status:** v1 in progress — the FastAPI app skeleton (routing, config, health check) is scaffolded; ingestion, retrieval, and generation logic are still being wired in. See [Roadmap](#roadmap) below.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Orchestration | LangChain (langchain-core, langchain-community, langchain-text-splitters) |
| LLM | Groq (openai/gpt-oss-120b) via langchain-groq |
| Embeddings | HuggingFace sentence-transformers (all-MiniLM-L6-v2) |
| Vector Store | pgvector on Neon Postgres |
| Validation | Pydantic v2 |
| Config | pydantic-settings (.env) |
| Frontend | v0 / Bolt-generated chat UI |
| Deployment | Render |

---

## Features

- **Document ingestion** — upload documents, chunked with `RecursiveCharacterTextSplitter`, embedded, and stored in pgvector *(in progress)*
- **Retrieval** — top-k similarity search over stored embeddings *(in progress)*
- **Generation** — retrieved context stuffed into a prompt and answered by Groq *(in progress)*
- **Sourced answers** — query responses return source chunks alongside the answer, for a frontend sources panel *(in progress)*
- **Environment-based config** via pydantic-settings and `.env`
- **Auto-generated API docs** at `/docs` (Swagger UI) and `/redoc`
- **Modular router structure** — documents and query in separate routers
- **CORS-enabled** for a separately-hosted frontend

---

## Project Structure

```
├── app/
│   ├── core/
│   │   └── config.py          # pydantic-settings environment config
│   ├── routers/
│   │   ├── documents.py       # POST /documents - ingestion endpoint
│   │   └── query.py           # POST /query - retrieval + generation endpoint
│   ├── services/
│   │   ├── ingestion.py       # loaders + text splitting (planned)
│   │   ├── retrieval.py       # pgvector store + retriever (planned)
│   │   └── generation.py      # prompt + LLM call (planned)
│   ├── models/
│   │   └── schemas.py         # Pydantic request/response models (planned)
│   └── main.py                # App entry point, router registration, CORS
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/documents` | Upload a document for ingestion *(stub — returns filename only)* |
| POST | `/query` | Ask a question over ingested documents *(stub — returns placeholder answer)* |
| GET | `/health` | Liveness check |

---

## Getting Started

**Prerequisites:**
- Python 3.10+
- A Neon Postgres instance with the `pgvector` extension enabled
- A Groq API key

```bash
# Clone the repo
git clone <your-repo-url>
cd rag-capstone

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create your .env file (see Environment Variables section below)
cp .env.example .env
```

Run the server:

```bash
uvicorn app.main:app --reload
```

API docs available at: `http://127.0.0.1:8000/docs`

---

## Environment Variables

Create a `.env` file in the root directory (see `.env.example`):

```env
GROQ_API_KEY=your_groq_api_key
DATABASE_URL=postgresql://user:password@host/dbname   # Neon connection string, pgvector-enabled
ALLOWED_ORIGINS=["http://localhost:3000"]
```

---

## Deployment

Target platform is **Render**, per the project roadmap. Deployment config (start command, port binding, environment-variable injection) is not yet set up.

---

## Roadmap

**v1 (in progress)**
- [x] FastAPI scaffold — app entrypoint, config, stub routers, health check
- [ ] Document ingestion + chunking (`RecursiveCharacterTextSplitter`)
- [ ] Embedding generation + pgvector storage
- [ ] Top-k similarity retrieval
- [ ] Generation (retrieve → prompt → Groq)
- [ ] v0/Bolt frontend (chat input, answer display, sources panel)
- [ ] Deploy to Render

**v2 (planned)**
- Conversational memory (`RunnableWithMessageHistory` + LangGraph checkpointing)
- Agentic behavior via `create_agent` + custom tools
- Hybrid search (BM25 + vector ensemble retriever)
- Reranking step between retrieval and generation
- Retrieval-quality upgrades: MMR, metadata filtering, self-query retrieval, contextual compression