"""
SM-2 spaced-repetition scheduler (the algorithm behind SuperMemo/Anki).

Why build retention scheduling into a research tool at all: reading a
paper once and chatting with it produces recognition, not recall. The
review loop is what turns "I read something about LoRA once" into
"I can explain LoRA's rank-decomposition trick from memory in a
meeting." This is the part no PDF-chat competitor does.

Reference: Wozniak, P.A. "SuperMemo 2 Algorithm" (1990).
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings

settings = get_settings()


@dataclass
class SchedulingState:
    ease_factor: float
    interval_days: int
    repetitions: int


def schedule_next_review(current: SchedulingState, quality: int) -> tuple[SchedulingState, datetime]:
    """
    Compute the next review state given a recall-quality grade.

    quality: 0-5 (0 = complete blackout, 5 = perfect, effortless recall).
    quality < 3 resets the repetition streak (the concept wasn't
    retained) but keeps the ease factor from collapsing entirely.
    """
    if not 0 <= quality <= 5:
        raise ValueError("quality must be between 0 and 5")

    ease = current.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ease = max(settings.SM2_MIN_EASE_FACTOR, ease)

    if quality < 3:
        repetitions = 0
        interval = 1
    else:
        repetitions = current.repetitions + 1
        if repetitions == 1:
            interval = 1
        elif repetitions == 2:
            interval = 6
        else:
            interval = round(current.interval_days * ease)

    next_review_at = datetime.now(timezone.utc) + timedelta(days=interval)
    return SchedulingState(ease_factor=ease, interval_days=interval, repetitions=repetitions), next_review_at
