# RAG Capstone

A retrieval-augmented generation (RAG) app built with **FastAPI** and **LangChain** on the backend, and a **Next.js** dashboard on the frontend, answering questions over user-uploaded documents. Embeddings are stored in **pgvector** on a hosted **Neon Postgres** instance, with generation running on **Groq**. This is the capstone project bridging the DeepLearning.AI LangChain short courses ("LLM Application Development" and "Chat With Your Data") into a deployable, production-shaped stack.

> **Status:** Backend v1 is code-complete and fully tested (65 passing tests, everything external mocked). The frontend dashboard's design is done. Currently wiring the UI to the live backend API. Deployment to Render is still ahead. See [Roadmap](#roadmap) below.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI |
| Orchestration | LangChain (langchain-core, langchain-community, langchain-text-splitters, langchain-classic) |
| LLM | Groq (openai/gpt-oss-120b) via langchain-groq |
| Embeddings | HuggingFace sentence-transformers (all-MiniLM-L6-v2) |
| Vector store | pgvector on Neon Postgres |
| Conversational memory | PostgresChatMessageHistory (langchain-postgres), session-scoped |
| Validation | Pydantic v2 |
| Config | pydantic-settings (.env) |
| Frontend | Next.js (App Router) + Tailwind + shadcn/ui, generated via v0 |
| Testing | pytest, all external services (DB, embedding model, Groq) mocked |
| Deployment | Render (planned) |

---

## Features

- **Document ingestion** — PDF, DOCX, and Notion exports (zip) via a single upload endpoint, plus web pages by URL, chunked with `RecursiveCharacterTextSplitter`, embedded, and stored in pgvector
- **Document management** — list ingested sources with chunk counts, delete a source and all of its chunks
- **Retrieval** — top-k similarity search over stored embeddings
- **Generation** — retrieved context stuffed into a prompt and answered by Groq
- **Sourced answers** — query responses return deduplicated source chunks alongside the answer, for the dashboard's sources panel
- **Conversational memory** — optional `session_id` on `/query` keeps a running history per conversation, persisted in Postgres
- **Environment-based config** via pydantic-settings and `.env`
- **Auto-generated API docs** at `/docs` (Swagger UI) and `/redoc`
- **Modular router structure** — documents and query in separate routers, thin routers delegating to a services layer
- **CORS-enabled** for the separately-hosted frontend
- **Tested** — 65 pytest tests across schemas, services, and routers, with the DB connection, embedding model, and Groq client all mocked so the suite needs no real credentials and is CI-ready

---

## Project Structure

```
GUS-RAG/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   └── config.py            #pydantic-settings environment config
│   │   ├── models/
│   │   │   └── schemas.py           #pydantic request/response models
│   │   ├── routers/
│   │   │   ├── documents.py         #document upload, list, and delete endpoints
│   │   │   └── query.py             #question-answering endpoint
│   │   ├── services/
│   │   │   ├── chat_history.py      #session-scoped Postgres chat history
│   │   │   ├── generation.py        #prompt + Groq call
│   │   │   ├── ingestion.py         #loaders + text splitting
│   │   │   ├── retrieval.py         #pgvector retriever
│   │   │   └── vectorstore.py       #pgvector store + embeddings
│   │   └── main.py                  #app entry point, router registration, CORS
│   ├── .env                         #not committed
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   ├── ui/
│   │   │   └── button.tsx
│   │   └── rag-dashboard.tsx        #main dashboard UI
│   ├── lib/
│   │   └── utils.ts
│   ├── components.json
│   ├── next.config.mjs
│   ├── package.json
│   └── tsconfig.json
├── tests/
│   ├── fixtures/                    #sample.pdf, sample.docx, sample_notion_export.zip
│   ├── conftest.py                  #shared fixtures + import-time service mocks
│   ├── test_chat_history.py
│   ├── test_documents.py
│   ├── test_generation.py
│   ├── test_ingestion.py
│   ├── test_query.py
│   ├── test_retrieval.py
│   ├── test_schemas.py
│   └── test_vectorstore.py
├── .gitignore
├── pytest.ini                       #pythonpath = backend, so tests import `app` directly
└── README.md
```

`backend/venv/` and `frontend/node_modules/` are local, gitignored, and omitted above.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Welcome message |
| GET | `/health` | Liveness check |
| GET | `/documents/` | List ingested documents, with source, type, and chunk count |
| POST | `/documents/upload` | Upload a PDF, DOCX, or Notion export (zip); type is auto-detected from the extension |
| POST | `/documents/web` | Ingest a web page by URL |
| DELETE | `/documents/{source_name}` | Delete a document and all of its vector chunks |
| POST | `/query` | Ask a question over ingested documents; accepts an optional `session_id` for conversational memory and an optional `k` (1–10) for how many chunks to retrieve |

---

## Getting Started

**Prerequisites:**
- Python 3.13+
- Node.js (for the frontend)
- A Neon Postgres instance with the `pgvector` extension enabled
- A Groq API key

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create your .env file (see Environment Variables section below)
```

Run the server from `backend/`:

```bash
uvicorn app.main:app --reload
```

API docs available at: `http://127.0.0.1:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Environment Variables

Create a `.env` file inside `backend/`:

```env
GROQ_API_KEY=your_groq_api_key
LLM_MODEL=openai/gpt-oss-120b                          # optional, this is the default
DATABASE_URL=postgresql://user:password@host/dbname    # Neon connection string, pgvector-enabled
ALLOWED_ORIGINS=["http://localhost:3000"]
```

---

## Testing

Run from the **repo root** (not `backend/`), so `pytest.ini`'s `pythonpath = backend` resolves correctly:

```bash
pytest
```

No real database, embedding model, or Groq key is needed. `tests/conftest.py` mocks the SQLAlchemy engine, the HuggingFace embeddings, the PGVector store, the psycopg connection, and the Groq client before any app code is imported, so the suite runs in under a second and is safe to drop straight into CI.

---

## Deployment

Target platform is **Render**, per the project roadmap. Deployment config (start command, port binding, environment-variable injection) is not yet set up.

---

## Roadmap

**v1**
- [x] FastAPI scaffold — app entrypoint, config, routers, health check
- [x] Document ingestion + chunking (`RecursiveCharacterTextSplitter`)
- [x] Embedding generation + pgvector storage
- [x] Document listing and deletion
- [x] Top-k similarity retrieval
- [x] Generation (retrieve → prompt → Groq)
- [x] Session-scoped conversational memory on `/query`
- [x] Backend test suite (pytest, 65 tests, CI-ready)
- [x] v0-generated frontend dashboard design
- [ ] Wire the frontend dashboard to the live backend API
- [ ] Deploy to Render

**v2 (planned)**
- Upgrade conversational memory to `RunnableWithMessageHistory` + LangGraph checkpointing (v1 ships a simpler session-scoped Postgres history as a stopgap)
- Agentic behavior via `create_agent` + custom tools
- Hybrid search (BM25 + vector ensemble retriever)
- Reranking step between retrieval and generation
- Retrieval-quality upgrades: MMR, metadata filtering, self-query retrieval, contextual compression