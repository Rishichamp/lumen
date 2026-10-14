# Lumen — Research Retention Copilot

**The gap Lumen closes:** you can chat with a paper (NotebookLM, Elicit)
and you can organize papers (Zotero), but nothing makes you *remember*
what you read a month later. Lumen adds a spaced-repetition retention
layer on top of RAG chat and semantic search, so reading a paper turns
into knowledge you can actually recall in a meeting or a thesis defense
— not just something you once queried.

Built as a portfolio-grade, production-structured full-stack
application: FastAPI + PostgreSQL backend, Next.js + TypeScript
frontend, real test coverage, Docker, and CI.

## What it does

- **Upload a PDF** → background pipeline extracts text, chunks it,
  embeds it locally (no API cost), indexes it, and generates a summary.
- **Chat with your library** → RAG-grounded answers with page-level
  citations you can trust enough to cite yourself.
- **Semantic search** → scan raw ranked passages when you don't want a
  generated answer, just the source.
- **Review queue** → SM-2-scheduled flashcards over key concepts, so
  retention compounds instead of decaying.
- **Command palette** (⌘K) → navigate the whole app without a mouse.

## Screenshots

See `docs/screenshots/` (or run it locally — `docker compose up --build`
gets you a running instance in one command).

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, TailwindCSS, Zustand, Framer Motion, cmdk |
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic v2 |
| Database | PostgreSQL (prod) / SQLite (dev) |
| Vector search | FAISS (per-user index) |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`, local CPU) |
| LLM | Any OpenAI-compatible endpoint (OpenAI, or a self-hosted/compatible alternative); graceful extractive fallback with no key configured |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Infra | Docker, Docker Compose, GitHub Actions CI |

Full rationale for each choice — including alternatives considered and
rejected — is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and the
ADRs in [`docs/adr/`](docs/adr/).

## Quickstart

```bash
export SECRET_KEY=$(openssl rand -hex 32)
docker compose up --build
```
Frontend: http://localhost:3000 · API docs: http://localhost:8000/api/docs

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for local dev without
Docker, and production deployment notes.

## Running tests

```bash
cd backend
pip install -r requirements.txt
pytest --cov=app --cov-report=term-missing
```
32 tests, 93% coverage on application code, covering: auth (hashing,
JWT roundtrip, tamper rejection), the full upload→ingest→search→chat
pipeline through the real HTTP API, cross-user access isolation, the
SM-2 spaced-repetition scheduler, and PDF chunking edge cases.

```bash
cd frontend
npx tsc --noEmit && npm test && npm run build
```
The frontend unit tests (Vitest) cover the API client: auth header, uploads,
204 handling and readable error messages for FastAPI validation errors.

## Project structure

```
lumen/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # auth, papers, chat, search, review
│   │   ├── core/             # config, security, deps
│   │   ├── db/                # SQLAlchemy engine/session
│   │   ├── models/            # ORM models (schema source of truth)
│   │   ├── schemas/            # Pydantic request/response contracts
│   │   └── services/          # PDF, embeddings, LLM, RAG, spaced repetition
│   ├── tests/
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                # Next.js App Router pages
│   │   ├── components/         # AppShell, CommandPalette
│   │   └── lib/                 # typed API client, auth store
│   └── Dockerfile
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT.md
│   └── adr/                     # architecture decision records
├── .github/workflows/ci.yml
└── docker-compose.yml
```

## Design notes worth reading

- **Citations are mandatory, not optional**, on every RAG answer — see
  `rag_service.py`. An answer a student can't trace to a page number is
  worse than no answer for academic use.
- **No API key required to run the full pipeline.** Embeddings run
  locally; without an LLM key, chat falls back to labeled extractive
  excerpts instead of failing or hallucinating.
- **Vector isolation is structural**, not a runtime filter: one FAISS
  file per user, so there's no `WHERE user_id = ?` to forget in a new
  endpoint (ADR-002).

## License

MIT — see `LICENSE`.
