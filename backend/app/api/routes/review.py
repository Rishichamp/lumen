"""Spaced-repetition review endpoints — the retention engine.

Cards are generated per-concept (see routes/concepts.py-equivalent logic
inline in papers ingestion in a future iteration) and reviewed here via
the SM-2 scheduler. `GET /review/due` is what the dashboard's daily
"Today's Reviews" widget polls.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.models import ReviewCard, User
from app.schemas.schemas import ReviewCardOut, ReviewGrade
from app.services.spaced_repetition import SchedulingState, schedule_next_review

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/due", response_model=list[ReviewCardOut])
def get_due_cards(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    return (
        db.query(ReviewCard)
        .filter(
            ReviewCard.user_id == current_user.id,
            ReviewCard.suspended.is_(False),
            ReviewCard.next_review_at <= now,
        )
        .order_by(ReviewCard.next_review_at.asc())
        .all()
    )


@router.post("/{card_id}/grade", response_model=ReviewCardOut)
def grade_card(
    card_id: int,
    payload: ReviewGrade,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewCardOut:
    card = db.get(ReviewCard, card_id)
    if card is None or card.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review card not found")

    current_state = SchedulingState(
        ease_factor=card.ease_factor, interval_days=card.interval_days, repetitions=card.repetitions
    )
    new_state, next_review_at = schedule_next_review(current_state, payload.quality)

    card.ease_factor = new_state.ease_factor
    card.interval_days = new_state.interval_days
    card.repetitions = new_state.repetitions
    card.next_review_at = next_review_at
    card.last_reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(card)

    return card
