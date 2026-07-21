# Lumen — System Architecture

## 1. Product summary

Lumen is a research retention copilot for AI/ML students and
researchers. It combines three things no single competitor combines:

| Capability | What it does | Why it's not "AI for marketing" |
|---|---|---|
| RAG chat | Ask questions across your paper library, grounded with page-level citations | Every answer traces to a source; ungrounded questions get an honest "not found," not a hallucination |
| Semantic search | Vector search across all ingested chunks | Faster than chat when you just want to scan raw passages yourself |
| Spaced-repetition review | SM-2-scheduled flashcards over key concepts | Converts "I chatted with this paper once" into durable recall — the actual gap in Zotero/Elicit/NotebookLM |

## 2. High-level architecture

```
┌─────────────────┐        HTTPS/JSON        ┌──────────────────────┐
│   Next.js SPA    │ ───────────────────────▶ │      FastAPI          │
│  (App Router,     │ ◀─────────────────────── │   (stateless, JWT)    │
│   Tailwind, Zustand)│                        └──────────┬───────────┘
└─────────────────┘                                       │
                                                            │
                        ┌───────────────────────────────────┼───────────────────────┐
                        │                                    │                       │
                 ┌──────▼──────┐                     ┌───────▼────────┐     ┌────────▼────────┐
                 │  PostgreSQL  │                     │  FAISS indexes  │     │  LLM provider    │
                 │ (users,      │                     │ (per-user,      │     │ (OpenAI-compat., │
                 │  papers,     │                     │  on disk volume)│     │  or extractive   │
                 │  chunks,     │                     └─────────────────┘     │  fallback if no  │
                 │  chat, SRS)  │                                              │  key configured) │
                 └──────────────┘                                              └──────────────────┘
```

## 3. Request flow: uploading and chatting with a paper

1. **Upload** (`POST /api/v1/papers`): file is validated as PDF, saved to
   the storage volume, a `Paper` row is created with `status=processing`,
   and ingestion is scheduled as a background task. The client gets an
   immediate response and polls `GET /papers/{id}` for status.
2. **Ingestion pipeline** (`IngestionPipeline.run`, off the request
   thread): extract per-page text (`pypdf`) → chunk into ~300-word
   overlapping windows → embed each chunk (`sentence-transformers`,
   local CPU inference, no external API call) → append vectors to the
   user's FAISS index → persist `Chunk` rows with their vector-row
   offset → generate a 3-sentence summary via the LLM client → mark
   `status=ready`.
3. **Chat** (`POST /api/v1/chat`): the question is embedded with the
   same model, the user's FAISS index is searched for the top-k
   nearest chunks (optionally scoped to one paper), a prompt is built
   with numbered sources, the LLM generates an answer instructed to
   cite only what's in the sources, and the response carries structured
   `citations` (paper, page, snippet) alongside the text.
4. **Review** (`GET /review/due`, `POST /review/{id}/grade`): concepts
   extracted from papers get scheduled flashcards; grading a card runs
   the SM-2 algorithm to compute the next interval and updates
   `next_review_at`.

## 4. Database schema (see `backend/app/models/models.py` for the source of truth)

- `users` — auth identity
- `papers` — one row per uploaded PDF, `status` tracks the ingestion pipeline
- `chunks` — retrieval units; `vector_row` points into the user's FAISS index
- `tags` / `paper_tags` — many-to-many classification
- `concepts` / `concept_mentions` — the knowledge-graph node/edge tables
- `chat_sessions` / `messages` — conversation history with JSON-encoded citations
- `review_cards` — SM-2 scheduling state per concept

Every user-owned table carries `user_id`; every route handler checks
ownership before returning or mutating a row (see `get_paper`,
`grade_card`, etc. — 404, not 403, on a mismatch, to avoid confirming
that a resource exists for another user).

## 5. Why these technology choices

| Decision | Chosen | Rejected alternatives | Why |
|---|---|---|---|
| Vector storage | FAISS, per-user file | Qdrant, Pinecone, pgvector | See ADR-002 — right-sized for single-user libraries, zero extra infra, structural isolation |
| Background jobs | FastAPI `BackgroundTasks` | Celery + Redis | See ADR-001 — right-sized for v1 upload volume; clean seam to migrate later |
| Embeddings | `sentence-transformers` (local) | OpenAI embeddings API | Free, works offline, no per-embedding cost at scale; generation (harder task) still uses a real LLM |
| Auth | Custom JWT + bcrypt | Auth0/Clerk | No per-seat SaaS cost for a portfolio/personal-scale project; the code is simple enough to own directly and audit |
| DB | SQLite (dev) / PostgreSQL (prod) | MongoDB | Relational data (users → papers → chunks → citations) is genuinely relational; SQL joins are simpler than aggregation pipelines here |
| Frontend state | Zustand | Redux, Context+useReducer | Minimal boilerplate for a small global auth store; component-local `useState` handles the rest |

## 6. Security posture

- Passwords hashed with bcrypt (adaptive cost factor), never logged or returned.
- JWT bearer tokens, HS256, configurable expiry, secret from environment.
- Every resource-owning endpoint checks `row.user_id == current_user.id` before returning data — verified in tests (`test_paper_not_found_for_other_user`, `test_cannot_grade_another_users_card`).
- CORS restricted to configured origins (not `*`).
- Global exception handler prevents stack traces from reaching clients; full detail goes to server logs only.
- File uploads validated by content-type before being written to disk.

## 7. Scalability path

Current design comfortably serves a single researcher or a small cohort
self-hosting their own instance (the realistic v1 audience). Scaling
to thousands of concurrent users would mean, roughly in this order:
1. Move ingestion to Celery + Redis (ADR-001).
2. Move vector storage to Qdrant with per-tenant collections (ADR-002).
3. Add Redis-backed rate limiting on `/chat` and `/papers` (LLM calls
   are the expensive resource).
4. Horizontal-scale the FastAPI process behind a load balancer — it's
   already stateless (JWT, no server-side sessions), so this is a
   straightforward win once ingestion/vectors are externalized.
5. Move file storage (uploaded PDFs) to S3-compatible object storage
   instead of a local volume, so any backend instance can serve any
   file.
