# Gus AI — RAG Capstone

A retrieval-augmented generation (RAG) app built with **FastAPI** and **LangChain** on the backend, and a **Next.js** dashboard on the frontend, answering questions over user-uploaded documents. Embeddings are generated via **Voyage AI** and stored in **pgvector** on a hosted **Neon Postgres** instance, with generation running on **Groq** and v2 retrieval reranked via **Cohere**.



## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI |
| Orchestration | LangChain (langchain-core, langchain-community, langchain-text-splitters, langchain-classic) |
| LLM | Groq (openai/gpt-oss-120b) via langchain-groq |
| Embeddings | Voyage AI (`VoyageAIEmbeddings`) via langchain-voyageai |
| Reranking | Cohere Rerank (`rerank-v3.5`) via langchain-cohere |
| Vector store | pgvector on Neon Postgres |
| Conversational memory | PostgresChatMessageHistory (langchain-postgres), session-scoped |
| Evaluation | RAGAS, run from a standalone `eval/` harness against real services |
| Validation | Pydantic v2 |
| Config | pydantic-settings (.env) |
| Frontend | Next.js (App Router) + Tailwind + shadcn/ui |
| Testing | pytest, all external services (DB, embedding model, Groq) mocked |
| CI/CD | GitHub Actions (test gate on PRs, auto-deploy to Render on `main`) |
| Deployment | Render (Backend via Docker) & Vercel (Frontend) |


## Features

- **Document ingestion** — PDF, DOCX, and Notion exports (zip) via a single upload endpoint, plus web pages by URL, chunked with `RecursiveCharacterTextSplitter`, embedded via Voyage AI, and stored in pgvector
- **Session-scoped multi-tenancy** — every ingested chunk, retrieval, and query is scoped by `session_id` end-to-end (ingestion, listing, deletion, vector search, BM25 corpus); a `session_id` is generated server-side and returned whenever a client omits one
- **Document management** — list and delete ingested sources (optionally scoped to a `session_id`), with chunk counts
- **Two-tier retrieval:**
  - **v1** — plain top-k similarity search (the eval baseline)
  - **v2** — hybrid dense + sparse search (self-query/MMR vector retrieval ensembled with BM25), Cohere reranking, contextual compression, and optional multi-hop question decomposition for questions that need more than one retrieval pass
- **Generation** — retrieved context stuffed into a prompt and answered by Groq
- **Sourced answers** — query responses return deduplicated source chunks alongside the answer, for the dashboard's sources panel
- **Conversational memory** — session-scoped running history on `/query`, persisted in Postgres
- **Evaluation harness** — RAGAS-based benchmarking of v1 vs. v2 (faithfulness, etc.) against real services, with timestamped results kept under `eval/results/`
- **Environment-based config** via pydantic-settings and `.env`
- **Auto-generated API docs** at `/docs` (Swagger UI) and `/redoc`
- **Modular router structure** — documents and query in separate routers, thin routers delegating to a services layer
- **CORS-enabled** for the separately-hosted frontend
- **CI/CD** — GitHub Actions runs the pytest suite on every push/PR, and auto-deploys to Render on push to `main`
- **Tested** — 61 pytest tests across schemas, services, and routers, with the DB connection, embedding model, and Groq client all mocked so the suite needs no real credentials and is CI-ready



## Project Structure

```text
GUS-RAG/
├── .github/
│   └── workflows/
│       ├── deploy.yml               #test, then trigger Render deploy on push to main
│       └── testing.yml              #test-only CI on push/PR to DEV, v1, v2
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
│   │   │   ├── retrieval.py         #v1 top-k + v2 hybrid search, reranking, compression
│   │   │   └── vectorstore.py       #pgvector store + Voyage embeddings
│   │   └── main.py                  #app entry point, router registration, CORS
│   ├── .env                         #not committed
│   ├── Dockerfile                   #production container config
│   └── requirements.txt
├── eval/
│   ├── results/                     #timestamped RAGAS run outputs, e.g. v2_k7_20261001T180649Z.json
│   ├── dataset.py                   #fixed question/ground-truth set used for every eval run
│   ├── requirements.txt             #eval-only deps (ragas, etc.), separate from backend/requirements.txt
│   └── run_eval.py                  #runs the RAGAS comparison against real services, not mocked
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
├── .dockerignore
├── .gitignore
├── pytest.ini                       #pythonpath = backend, so tests import `app` directly
└── README.md
```

`backend/venv/`, `frontend/node_modules/`, and `eval/__pycache__/` are local, gitignored, and omitted above.



## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Welcome message |
| GET | `/health` | Liveness check |
| GET | `/documents/` | List ingested documents, optionally filtered by `session_id`, with source, type, and chunk count |
| POST | `/documents/upload` | Upload a PDF, DOCX, or Notion export (zip) as multipart form data; type is auto-detected from the extension. `session_id` is an optional form field — a new one is generated and returned if omitted |
| POST | `/documents/web` | Ingest a web page by URL (JSON body); `session_id` is optional, generated and returned if omitted |
| DELETE | `/documents/{source_name}` | Delete a document and all of its vector chunks, optionally scoped to a `session_id` |
| POST | `/query/` | Ask a question over ingested documents, scoped to `session_id` (generated if omitted); `version` (`v1` default or `v2`) selects the retrieval strategy. `k` is fixed server-side (default 7) and intentionally not client-configurable — only the eval harness varies it |



## Getting Started

**Prerequisites:**

- Python 3.13+
- Node.js (for the frontend)
- A Neon Postgres instance with the `pgvector` extension enabled
- A Groq API key
- A Voyage AI API key
- A Cohere API key (for v2's reranking step)
- Docker (optional, for local container testing)

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
uvicorn app.main:app --reload --port 8000
```

API docs available at: `http://127.0.0.1:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```



## Environment Variables

Create a `.env` file inside `backend/`:

```env
GROQ_API_KEY=your_groq_api_key
LLM_MODEL=openai/gpt-oss-120b                          # optional, this is the default
VOYAGE_API_KEY=your_voyage_api_key
VOYAGE_MODEL=your_voyage_model                         # see app/core/config.py for the current default
COHERE_API_KEY=your_cohere_api_key                     # required for v2's reranking step
DATABASE_URL=postgresql://user:password@host/dbname    # Neon connection string, pgvector-enabled
ALLOWED_ORIGINS=["http://localhost:3000", "https://your-frontend-domain.vercel.app"]
```

A handful of retrieval-tuning knobs (BM25 weight, fetch-k multiplier, multi-hop subquestion cap, default `k`, ingestion batch size) also live in `app/core/config.py` with sane defaults — override them via `.env` only if you need to.

Create a `.env.local` file inside `frontend/`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000              
```
Replace with Render URL in production



## Testing

Run from the **repo root** (not `backend/`), so `pytest.ini`'s `pythonpath = backend` resolves correctly:

```bash
pytest
```

No real database, embedding model, or Groq key is needed. `tests/conftest.py` mocks the SQLAlchemy engine, the embedding model, the PGVector store, the psycopg connection, and the Groq client before any app code is imported, so the suite runs in under a second and is safe to drop straight into CI.



## Evaluation (RAGAS)

Separate from the pytest suite, `eval/` runs a RAGAS-based comparison of the v1 and v2 retrieval strategies against real services (actual Groq calls, actual pgvector lookups), not mocks — so it needs real credentials in `backend/.env`.

```bash
# Usage: (pick either v1 or v2, along with k: 1<=k<=10)
cd eval
pip install -r requirements.txt
python eval/run_eval.py v2 --k 7
```

- `dataset.py` holds the fixed question/ground-truth set used for every run, so v1 and v2 are benchmarked against the same questions.
  
- `run_eval.py` computes the RAGAS metrics and writes a timestamped result file to `eval/results/`, so past runs are kept rather than overwritten.



## CI/CD

Two GitHub Actions workflows live in `.github/workflows/`, split by branch:

| Workflow | Triggers on | Does |
|---|---|---|
| `testing.yml` | Push/PR to `DEV`, `PR` to `v1` / `v2` | Runs the pytest suite only — CI gate for in-progress work |
| `deploy.yml` | Push to `main` | Runs the pytest suite, then (on success) hits the Render deploy hook to ship the backend |

Both jobs check out the repo, set up Python 3.13, install `backend/requirements.txt`, and run `pytest -v`. `GROQ_API_KEY`, `VOYAGE_API_KEY`, `COHERE_API_KEY`, `DATABASE_URL`, and `ALLOWED_ORIGINS` are all pulled from **GitHub Secrets**

`deploy.yml`'s `deploy` job depends on `test` passing and calls `RENDER_DEPLOY_HOOK_URL` (a repo secret) to trigger a new Render deployment; Render then rebuilds and redeploys the Docker service directly from `main`. Vercel handles the frontend separately via its own Git integration and isn't part of these workflows.



## Deployment

### Backend (Render)

The FastAPI backend is deployed as a Docker Web Service on **Render**.

- Embeddings (Voyage) and reranking (Cohere) are both external API calls.
  
- Ensure `DATABASE_URL`, `GROQ_API_KEY`, `VOYAGE_API_KEY`, and `COHERE_API_KEY` are set in the Render environment dashboard.

### Frontend (Vercel)

The Next.js frontend is deployed to **Vercel**.

- Add the `NEXT_PUBLIC_API_URL` environment variable to your Vercel project settings, pointing it to the live Render backend URL.
  
- Ensure the backend's CORS configuration (`ALLOWED_ORIGINS` in `main.py` / Render environment variables) is updated to accept traffic from your live Vercel domain.



## Known Limitations

- **No user accounts or authentication.** The app scopes everything by an ephemeral `session_id` (client- or server-generated) rather than a logged-in user — there's no login system and no storage of user credentials.
  
- **No long-term, per-account chat history or file retention.** Conversational memory and ingested chunks are scoped to a `session_id`, but original uploaded files aren't retained after chunking — only their text chunks and embeddings are stored.




## Roadmap

**V1**
- [x] FastAPI scaffold — app entrypoint, config, routers, health check
- [x] Document ingestion + chunking (`RecursiveCharacterTextSplitter`)
- [x] Embedding generation + pgvector storage
- [x] Document listing and deletion
- [x] Top-k similarity retrieval
- [x] Generation (retrieve → prompt → Groq)
- [x] Session-scoped conversational memory on `/query`
- [x] Session-scoped multi-tenant isolation across ingestion, retrieval, and deletion, including hardening the self-query retriever against cross-session leakage
- [x] Backend test suite (pytest, 61 tests, CI-ready)
- [x] GitHub Actions CI/CD — test gate on PRs, auto-deploy to Render on `main`
- [x] v0-generated frontend dashboard design
- [x] Wire the frontend dashboard to the live backend API
- [x] Deploy to Render (Backend) and Vercel (Frontend)

**V2**
- [x] Hybrid search (BM25 + vector ensemble retriever)
- [x] Reranking step between retrieval and generation (Cohere)
- [x] Retrieval-quality upgrades: MMR, metadata filtering, self-query retrieval, contextual compression, multi-hop retrievals
- [x] Eval harness (RAGAS), benchmarking v1 vs. v2 on retrieval precision and faithfulness
- [ ] Agentic behavior via `create_agent` + custom tools