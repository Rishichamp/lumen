"""
SQLAlchemy engine/session wiring.

DATABASE_URL drives dialect selection: sqlite for local dev/tests
(zero-setup, file-based), postgresql+psycopg for production (see
docker-compose.yml). The rest of the app never imports a dialect
directly, so switching is a one-line env change.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

_connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
