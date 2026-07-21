"""
Domain models.

Schema design notes
--------------------
- Every user-owned table carries `user_id` for row-level isolation; the
  API layer never trusts a client-supplied id without checking ownership.
- `Chunk.vector_row` is the integer offset of this chunk's embedding
  inside the user's FAISS index file (one FAISS index per user keeps
  indexes small, fast to load, and trivially deletable on account
  deletion — see services/embedding_service.py).
- `Concept` + `ConceptMention` form a lightweight knowledge graph:
  concepts are nodes, mentions (concept <-> paper) are edges. This is
  intentionally simpler than a full graph DB (Neo4j) because the scale
  (one user's paper library, thousands of nodes at most) doesn't
  justify the operational cost — a relational adjacency model is
  faster to ship and easier to query with SQL joins.
- `ReviewCard` implements the SM-2 spaced-repetition schedule
  (see services/spaced_repetition.py) directly on the row so scheduling
  a review is a single UPDATE, not a separate event log.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    papers: Mapped[list["Paper"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    chat_sessions: Mapped[list["ChatSession"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    concepts: Mapped[list["Concept"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    review_cards: Mapped[list["ReviewCard"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    authors: Mapped[str] = mapped_column(String(1000), default="")
    abstract: Mapped[str] = mapped_column(Text, default="")
    arxiv_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="processing")  # processing|ready|failed
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    owner: Mapped["User"] = relationship(back_populates="papers")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="paper", cascade="all, delete-orphan")
    tags: Mapped[list["Tag"]] = relationship(secondary="paper_tags", back_populates="papers")
    concept_mentions: Mapped[list["ConceptMention"]] = relationship(back_populates="paper", cascade="all, delete-orphan")


class Chunk(Base):
    """A retrieval unit: one chunk of a paper's text plus its vector index pointer."""

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id"), index=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, default=0)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    vector_row: Mapped[int] = mapped_column(Integer, nullable=False)  # offset in user's FAISS index

    paper: Mapped["Paper"] = relationship(back_populates="chunks")


class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    papers: Mapped[list["Paper"]] = relationship(secondary="paper_tags", back_populates="tags")


class PaperTag(Base):
    __tablename__ = "paper_tags"
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), primary_key=True)


class Concept(Base):
    """A node in the personal knowledge graph (e.g. 'contrastive learning')."""

    __tablename__ = "concepts"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_concept_user_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    owner: Mapped["User"] = relationship(back_populates="concepts")
    mentions: Mapped[list["ConceptMention"]] = relationship(back_populates="concept", cascade="all, delete-orphan")
    review_cards: Mapped[list["ReviewCard"]] = relationship(back_populates="concept", cascade="all, delete-orphan")


class ConceptMention(Base):
    """Edge: concept <-> paper (the knowledge graph edge table)."""

    __tablename__ = "concept_mentions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id"), index=True, nullable=False)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id"), index=True, nullable=False)
    relevance: Mapped[float] = mapped_column(Float, default=1.0)

    concept: Mapped["Concept"] = relationship(back_populates="mentions")
    paper: Mapped["Paper"] = relationship(back_populates="concept_mentions")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="New chat")
    scope_paper_id: Mapped[int | None] = mapped_column(ForeignKey("papers.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    owner: Mapped["User"] = relationship(back_populates="chat_sessions")
    messages: Mapped[list["Message"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user|assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list] = mapped_column(JSON, default=list)  # [{paper_id, chunk_id, page}]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")


class ReviewCard(Base):
    """A spaced-repetition flashcard scheduled with the SM-2 algorithm."""

    __tablename__ = "review_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id"), index=True, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)

    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    interval_days: Mapped[int] = mapped_column(Integer, default=0)
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    next_review_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    suspended: Mapped[bool] = mapped_column(Boolean, default=False)

    owner: Mapped["User"] = relationship(back_populates="review_cards")
    concept: Mapped["Concept"] = relationship(back_populates="review_cards")
