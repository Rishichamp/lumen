"""
Paper library endpoints.

Ingestion runs as a FastAPI BackgroundTask so the upload request returns
immediately (status="processing") and the UI polls/refetches for
status="ready". At current expected scale (a single user uploading a
handful of papers at a time) this avoids standing up Celery+Redis; the
`IngestionPipeline` class is isolated behind one call so swapping to a
Celery task is a matter of decorating `run()` with `@celery_app.task`
and calling `.delay()` instead of `background_tasks.add_task()" —
documented as the scale-out path in docs/adr/ADR-001.
"""
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.db.database import SessionLocal, get_db
from app.models.models import Chunk, Paper, Tag
from app.schemas.schemas import PaperListItem, PaperOut
from app.services.embedding_service import SentenceTransformerEmbedder, VectorIndexStore
from app.services.llm_service import get_llm_client
from app.services.pdf_service import chunk_pages, extract_pages, extract_title_and_abstract
from app.services.rag_service import summarize_paper
from app.models.models import User

router = APIRouter(prefix="/papers", tags=["papers"])
settings = get_settings()
_index_store = VectorIndexStore()

# Background tasks run outside FastAPI's request scope, so they can't use
# `Depends(get_db)`. This module-level factory is the seam instead: tests
# monkeypatch it to point at the same isolated test engine used by the
# `get_db` dependency override, so a paper created via the API and one
# updated by the background task land in the same database. Without this
# seam, the background task would silently keep using the production
# SessionLocal even while requests were redirected to a test database.
_session_factory = SessionLocal


class IngestionPipeline:
    """Runs off the request thread: extract -> chunk -> embed -> index -> summarize."""

    def __init__(self, paper_id: int, user_id: int):
        self.paper_id = paper_id
        self.user_id = user_id

    def run(self) -> None:
        db = _session_factory()
        try:
            paper = db.get(Paper, self.paper_id)
            if paper is None:
                return
            try:
                pages = extract_pages(paper.file_path)
                title, abstract = extract_title_and_abstract(pages)
                extracted_chunks = chunk_pages(pages, settings.CHUNK_SIZE_TOKENS, settings.CHUNK_OVERLAP_TOKENS)

                if not extracted_chunks:
                    paper.status = "failed"
                    paper.summary = "No extractable text found (the PDF may be a scanned image)."
                    db.commit()
                    return

                embedder = SentenceTransformerEmbedder()
                vectors = embedder.embed([c.content for c in extracted_chunks])
                start_row = _index_store.add(self.user_id, vectors)

                for offset, extracted in enumerate(extracted_chunks):
                    db.add(
                        Chunk(
                            paper_id=paper.id,
                            content=extracted.content,
                            page_number=extracted.page_number,
                            chunk_index=extracted.chunk_index,
                            vector_row=start_row + offset,
                        )
                    )

                llm_client = get_llm_client()
                summary_source = " ".join(p for p in pages[:3])
                paper.title = paper.title or title
                paper.abstract = paper.abstract or abstract
                paper.summary = summarize_paper(summary_source, llm_client)
                paper.page_count = len(pages)
                paper.status = "ready"
                db.commit()
            except Exception as exc:  # noqa: BLE001 - surfaced to the user via status field
                paper.status = "failed"
                paper.summary = f"Processing failed: {exc}"
                db.commit()
        finally:
            db.close()


@router.post("", response_model=PaperOut, status_code=status.HTTP_201_CREATED)
async def upload_paper(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaperOut:
    if file.content_type != "application/pdf":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only PDF files are supported")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}.pdf"
    dest_path = os.path.join(settings.UPLOAD_DIR, safe_name)

    # The browser-supplied content type is only a hint: check the PDF magic
    # bytes, and cap the size so one huge upload can't exhaust memory/disk.
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    contents = await file.read(max_bytes + 1)
    if len(contents) > max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            f"PDF is larger than {settings.MAX_UPLOAD_MB} MB")
    if not contents.startswith(b"%PDF-"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is not a valid PDF")
    with open(dest_path, "wb") as f:
        f.write(contents)

    paper = Paper(
        user_id=current_user.id,
        title=file.filename or "Untitled",
        filename=file.filename or safe_name,
        file_path=dest_path,
        status="processing",
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)

    background_tasks.add_task(IngestionPipeline(paper.id, current_user.id).run)

    return PaperOut.from_orm_with_tags(paper)


@router.get("", response_model=list[PaperListItem])
def list_papers(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[PaperListItem]:
    papers = (
        db.query(Paper)
        .filter(Paper.user_id == current_user.id)
        .order_by(Paper.created_at.desc())
        .all()
    )
    return [
        PaperListItem(
            id=p.id, title=p.title, authors=p.authors, status=p.status,
            created_at=p.created_at, tags=[t.name for t in p.tags],
        )
        for p in papers
    ]


@router.get("/{paper_id}", response_model=PaperOut)
def get_paper(paper_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> PaperOut:
    paper = db.get(Paper, paper_id)
    if paper is None or paper.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paper not found")
    return PaperOut.from_orm_with_tags(paper)


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paper(paper_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> None:
    paper = db.get(Paper, paper_id)
    if paper is None or paper.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paper not found")

    if os.path.exists(paper.file_path):
        os.remove(paper.file_path)
    db.delete(paper)
    db.commit()
    # Note: vector rows for this paper's chunks remain in the FAISS index
    # (FAISS IndexFlatIP doesn't support cheap row deletion). They become
    # unreachable dead weight until a periodic reindex compaction job
    # rebuilds the index from remaining chunks — tracked in the roadmap.
