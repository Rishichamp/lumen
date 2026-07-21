"""
Lumen API — application entrypoint.

Responsibilities kept here and nowhere else: middleware registration,
router mounting, global exception handling, structured logging setup,
and startup table creation (for demo/dev; production uses Alembic
migrations — see docs/DEPLOYMENT.md).
"""
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, chat, papers, review, search
from app.core.config import get_settings
from app.db.database import Base, engine

settings = get_settings()

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("lumen")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Dev/test convenience only. Production schema changes go through
    # Alembic migrations so rollouts are reviewable and reversible
    # (see docs/DEPLOYMENT.md).
    if settings.ENV != "production":
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables ensured (dev mode).")
    yield
    logger.info("Shutting down Lumen API.")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="AI Research Retention Copilot — RAG chat, semantic search, "
    "and spaced-repetition review over your personal paper library.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Attach a request id to every request/response for traceable logs,
    and log method/path/status/latency — the minimum needed to debug
    production incidents without a dedicated APM tool."""
    request_id = str(uuid.uuid4())[:8]
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "[%s] %s %s -> %s (%.1fms)",
        request_id, request.method, request.url.path, response.status_code, duration_ms,
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Never leak stack traces to clients; log full detail server-side."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(papers.router, prefix=settings.API_V1_PREFIX)
app.include_router(chat.router, prefix=settings.API_V1_PREFIX)
app.include_router(search.router, prefix=settings.API_V1_PREFIX)
app.include_router(review.router, prefix=settings.API_V1_PREFIX)


@app.get("/api/health", tags=["health"])
def health_check() -> dict:
    return {"status": "ok", "env": settings.ENV}
