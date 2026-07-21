"""Pydantic v2 schemas — the API's public contract, kept separate from ORM models
so internal columns (hashed_password, vector_row, etc.) are never leaked."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Papers ----------
class PaperOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    authors: str
    abstract: str
    arxiv_id: str | None
    status: str
    page_count: int
    summary: str
    created_at: datetime
    tags: list[str] = []

    @classmethod
    def from_orm_with_tags(cls, paper) -> "PaperOut":
        data = cls.model_validate(paper).model_dump()
        data["tags"] = [t.name for t in paper.tags]
        return cls(**data)


class PaperListItem(BaseModel):
    id: int
    title: str
    authors: str
    status: str
    created_at: datetime
    tags: list[str] = []


# ---------- Chat / RAG ----------
class ChatRequest(BaseModel):
    session_id: int | None = None
    message: str = Field(min_length=1, max_length=4000)
    scope_paper_id: int | None = None  # None = search whole library


class Citation(BaseModel):
    paper_id: int
    paper_title: str
    chunk_id: int
    page_number: int
    snippet: str


class ChatResponse(BaseModel):
    session_id: int
    answer: str
    citations: list[Citation]


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    content: str
    citations: list
    created_at: datetime


class ChatSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    scope_paper_id: int | None
    created_at: datetime


# ---------- Semantic search ----------
class SearchResult(BaseModel):
    paper_id: int
    paper_title: str
    chunk_id: int
    page_number: int
    snippet: str
    score: float


# ---------- Knowledge graph ----------
class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # "paper" | "concept"
    weight: int = 1


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: float = 1.0


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# ---------- Spaced repetition ----------
class ReviewCardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    concept_id: int
    question: str
    answer: str
    interval_days: int
    repetitions: int
    next_review_at: datetime


class ReviewGrade(BaseModel):
    quality: int = Field(ge=0, le=5, description="0=total blackout ... 5=perfect recall (SM-2 scale)")
