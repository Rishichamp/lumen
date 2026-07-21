from app.services.spaced_repetition import SchedulingState, schedule_next_review


def fresh_card() -> SchedulingState:
    return SchedulingState(ease_factor=2.5, interval_days=0, repetitions=0)


def test_perfect_recall_progresses_through_standard_intervals():
    state = fresh_card()

    state, _ = schedule_next_review(state, quality=5)
    assert state.repetitions == 1
    assert state.interval_days == 1

    state, _ = schedule_next_review(state, quality=5)
    assert state.repetitions == 2
    assert state.interval_days == 6

    state, _ = schedule_next_review(state, quality=5)
    assert state.repetitions == 3
    assert state.interval_days == round(6 * state.ease_factor)


def test_failed_recall_resets_repetitions_but_not_ease_below_minimum():
    state = fresh_card()
    state, _ = schedule_next_review(state, quality=5)
    state, _ = schedule_next_review(state, quality=5)

    state, _ = schedule_next_review(state, quality=1)  # forgot it
    assert state.repetitions == 0
    assert state.interval_days == 1


def test_ease_factor_never_drops_below_configured_minimum():
    state = fresh_card()
    for _ in range(20):
        state, _ = schedule_next_review(state, quality=0)
    assert state.ease_factor >= 1.3


def test_next_review_at_is_in_the_future():
    from datetime import datetime, timezone

    state = fresh_card()
    _, next_review_at = schedule_next_review(state, quality=4)
    assert next_review_at > datetime.now(timezone.utc)


def test_invalid_quality_raises():
    import pytest

    with pytest.raises(ValueError):
        schedule_next_review(fresh_card(), quality=6)
    with pytest.raises(ValueError):
        schedule_next_review(fresh_card(), quality=-1)
