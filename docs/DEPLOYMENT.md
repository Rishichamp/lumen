# Deployment Guide

## Local development (no Docker)

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in SECRET_KEY at minimum
uvicorn app.main:app --reload --port 8000
```
API docs at `http://localhost:8000/api/docs`.

**Frontend**
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```
App at `http://localhost:3000`.

Leave `OPENAI_API_KEY` empty in `.env` to run the full pipeline (upload,
embed, retrieve, cite) without a paid API key — chat answers come back
as labeled extractive excerpts instead of generated text. Add a real
key to get generated answers and paper summaries.

## Docker Compose (recommended for self-hosting)

```bash
export SECRET_KEY=$(openssl rand -hex 32)
export OPENAI_API_KEY=sk-...   # optional
docker compose up --build
```
This starts Postgres, the FastAPI backend, and the Next.js frontend
together, wired via the compose network. Data persists in named
volumes (`postgres_data`, `backend_storage`) across restarts.

## Production considerations

- **Migrations**: the app auto-creates tables on startup only when
  `ENV != production`. In production, manage schema changes with
  Alembic (`alembic init`, generate a migration per schema change,
  run `alembic upgrade head` as a deploy step) so rollouts are
  reviewable and reversible — auto-`create_all` in prod risks silent,
  unreviewed schema drift.
- **Secrets**: never commit `.env`. Use your platform's secret manager
  (e.g. a Kubernetes Secret, Fly.io secrets, or Vercel/Render env vars)
  for `SECRET_KEY` and `OPENAI_API_KEY`.
- **CORS**: set `CORS_ORIGINS` to your actual frontend domain(s), not
  `*`, once deployed.
- **Storage volume**: `backend_storage` holds uploaded PDFs and FAISS
  index files. Back it up like any other stateful volume — it's not
  reconstructable from Postgres alone.
- **HTTPS**: terminate TLS at a reverse proxy (Caddy, Nginx, or your
  cloud provider's load balancer) in front of both services; neither
  app serves TLS directly.
- **Frontend hosting**: `output: "standalone"` in `next.config.mjs`
  produces a minimal self-contained server — deployable equally well
  on Vercel, a container platform, or a plain VM.

## CI/CD

`.github/workflows/ci.yml` runs on every push/PR to `main`:
1. Backend: install deps, run the full pytest suite with coverage.
2. Frontend: typecheck, lint, production build.
3. Build both Docker images to catch Dockerfile regressions early.

Add a deploy job (e.g. push images to a registry, trigger a Fly.io/
Render/Kubernetes rollout) once you have a target environment —
intentionally left out here since it's specific to your hosting choice.
