# ADR-001: FastAPI BackgroundTasks over Celery for paper ingestion

## Status
Accepted (v1). Revisit when scale triggers described below are hit.

## Context
Ingesting an uploaded paper (extract → chunk → embed → index → summarize)
takes anywhere from 2–15 seconds depending on page count and whether an
LLM call is involved. This can't block the HTTP response.

## Decision
Use FastAPI's built-in `BackgroundTasks` for v1, not Celery + Redis.

## Rationale
- At expected initial scale (a single researcher uploading papers in
  small batches, not a firehose of concurrent uploads across thousands
  of users), a background task running in the same process is
  sufficient and removes an entire infrastructure component (broker,
  worker pool, task result backend) from the deployment.
- The `IngestionPipeline` class in `app/api/routes/papers.py` is
  isolated behind a single `.run()` method with no FastAPI-specific
  code inside it. Moving to Celery later is: decorate `run` with
  `@celery_app.task`, call `.delay()` instead of
  `background_tasks.add_task()`, and point ingestion at a Redis broker.
  No business logic changes.

## When to revisit
- Concurrent uploads start queuing behind each other and blocking
  server capacity (BackgroundTasks run in the same event loop's thread
  pool — they don't scale horizontally across processes/machines).
- Ingestion needs to survive a server restart (BackgroundTasks are
  lost if the process dies mid-task; Celery persists tasks in the
  broker).
- Multi-tenant scale requires per-tenant rate limiting or prioritization
  of ingestion jobs — Celery's queue routing handles this; a single
  process's background tasks do not.
