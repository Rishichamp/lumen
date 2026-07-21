"""
Retrieval-Augmented Generation pipeline.

Flow: query -> embed -> vector search (optionally scoped to one paper)
-> assemble grounded prompt with numbered sources -> LLM generation ->
map cited source numbers back to (paper, page, chunk) for the UI.

Why citations are mandatory here (not optional): the entire product
thesis is trustworthy recall for research work. An answer a student
can't trace back to a page number is actively worse than no answer —
it invites citing something in a thesis that doesn't say what the
model claimed. So `answer_question` always returns structured
citations alongside the text, and the system prompt instructs the
model to only assert what the sources support.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.models import Chunk, Paper
from app.services.embedding_service import Embedder, VectorIndexStore
from app.services.llm_service import LLMClient
from app.schemas.schemas import Citation

settings = get_settings()

SYSTEM_PROMPT = (
    "You are Lumen, a research assistant for an AI/ML graduate student. "
    "Answer ONLY using the numbered sources provided in the context. "
    "If the sources don't contain the answer, say so explicitly instead "
    "of guessing. Every factual claim must reference a source number "
    "like [1] or [2]. Be precise and concise — this answer may be used "
    "in academic work."
)


@dataclass
class RetrievedChunk:
    chunk: Chunk
    paper: Paper
    score: float


def retrieve(
    db: Session,
    user_id: int,
    query: str,
    embedder: Embedder,
    index_store: VectorIndexStore,
    top_k: int = settings.TOP_K_RETRIEVAL,
    scope_paper_id: int | None = None,
) -> list[RetrievedChunk]:
    query_vector = embedder.embed([query])[0]

    # Over-fetch when scoping to one paper, since the flat per-user index
    # mixes all papers together and we filter client-side afterward.
    fetch_k = top_k * 8 if scope_paper_id else top_k
    row_ids, scores = index_store.search(user_id, query_vector, fetch_k)
    if not row_ids:
        return []

    chunks = (
        db.query(Chunk)
        .join(Paper)
        .filter(Chunk.vector_row.in_(row_ids), Paper.user_id == user_id)
        .all()
    )
    chunk_by_row = {c.vector_row: c for c in chunks}

    results: list[RetrievedChunk] = []
    for row_id, score in zip(row_ids, scores):
        chunk = chunk_by_row.get(row_id)
        if chunk is None:
            continue
        if scope_paper_id is not None and chunk.paper_id != scope_paper_id:
            continue
        results.append(RetrievedChunk(chunk=chunk, paper=chunk.paper, score=float(score)))
        if len(results) >= top_k:
            break

    return results


def _build_prompt(query: str, retrieved: list[RetrievedChunk]) -> str:
    sources = "\n\n".join(
        f"[{i+1}] (Paper: \"{r.paper.title}\", page {r.chunk.page_number})\n{r.chunk.content}"
        for i, r in enumerate(retrieved)
    )
    return f"CONTEXT:\n{sources}\n\nQUESTION: {query}"


def answer_question(
    db: Session,
    user_id: int,
    query: str,
    embedder: Embedder,
    index_store: VectorIndexStore,
    llm_client: LLMClient,
    scope_paper_id: int | None = None,
) -> tuple[str, list[Citation]]:
    retrieved = retrieve(db, user_id, query, embedder, index_store, scope_paper_id=scope_paper_id)

    if not retrieved:
        return (
            "I couldn't find anything relevant in your library yet. "
            "Try uploading a paper first, or rephrase your question.",
            [],
        )

    prompt = _build_prompt(query, retrieved)
    answer = llm_client.generate(SYSTEM_PROMPT, prompt)

    citations = [
        Citation(
            paper_id=r.paper.id,
            paper_title=r.paper.title,
            chunk_id=r.chunk.id,
            page_number=r.chunk.page_number,
            snippet=r.chunk.content[:280],
        )
        for r in retrieved
    ]
    return answer, citations


def summarize_paper(text_sample: str, llm_client: LLMClient) -> str:
    """One-shot summary generated right after ingestion, shown on the
    library card before the user opens the paper."""
    system = (
        "Summarize this AI/ML research paper excerpt in 3 sentences: "
        "(1) the problem it addresses, (2) the core method/contribution, "
        "(3) the key result. Be precise, no fluff."
    )
    return llm_client.generate(system, text_sample[:6000])
