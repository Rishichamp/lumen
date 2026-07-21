"""Semantic (vector) search across a user's paper library — distinct from
chat: this returns ranked raw passages fast, for when the user wants to
scan sources themselves rather than read a generated answer."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.models import User
from app.schemas.schemas import SearchResult
from app.services.embedding_service import SentenceTransformerEmbedder, VectorIndexStore
from app.services.rag_service import retrieve

router = APIRouter(prefix="/search", tags=["search"])
_index_store = VectorIndexStore()
_embedder = SentenceTransformerEmbedder()


@router.get("", response_model=list[SearchResult])
def semantic_search(
    q: str = Query(min_length=1, max_length=500),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SearchResult]:
    results = retrieve(db, current_user.id, q, _embedder, _index_store, top_k=limit)
    return [
        SearchResult(
            paper_id=r.paper.id,
            paper_title=r.paper.title,
            chunk_id=r.chunk.id,
            page_number=r.chunk.page_number,
            snippet=r.chunk.content[:300],
            score=r.score,
        )
        for r in results
    ]
