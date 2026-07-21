"""RAG chat endpoints: create/list sessions, send a message, get grounded answer + citations."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.models import ChatSession, Message, User
from app.schemas.schemas import ChatRequest, ChatResponse, ChatSessionOut, MessageOut
from app.services.embedding_service import SentenceTransformerEmbedder, VectorIndexStore
from app.services.llm_service import get_llm_client
from app.services.rag_service import answer_question

router = APIRouter(prefix="/chat", tags=["chat"])
_index_store = VectorIndexStore()
_embedder = SentenceTransformerEmbedder()


@router.get("/sessions", response_model=list[ChatSessionOut])
def list_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )


@router.get("/sessions/{session_id}/messages", response_model=list[MessageOut])
def get_session_messages(session_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    session = db.get(ChatSession, session_id)
    if session is None or session.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat session not found")
    return session.messages


@router.post("", response_model=ChatResponse)
def send_message(payload: ChatRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ChatResponse:
    if payload.session_id is not None:
        session = db.get(ChatSession, payload.session_id)
        if session is None or session.user_id != current_user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat session not found")
    else:
        session = ChatSession(
            user_id=current_user.id,
            title=payload.message[:60],
            scope_paper_id=payload.scope_paper_id,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    db.add(Message(session_id=session.id, role="user", content=payload.message, citations=[]))
    db.commit()

    llm_client = get_llm_client()
    answer, citations = answer_question(
        db=db,
        user_id=current_user.id,
        query=payload.message,
        embedder=_embedder,
        index_store=_index_store,
        llm_client=llm_client,
        scope_paper_id=payload.scope_paper_id or session.scope_paper_id,
    )

    db.add(
        Message(
            session_id=session.id,
            role="assistant",
            content=answer,
            citations=[c.model_dump() for c in citations],
        )
    )
    db.commit()

    return ChatResponse(session_id=session.id, answer=answer, citations=citations)
