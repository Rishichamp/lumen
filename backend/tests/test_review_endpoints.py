from app.core.security import decode_access_token
from app.models.models import Concept, ReviewCard


def _seed_review_card(client, user_id: int, question: str = "What is self-attention?") -> int:
    db = client.db_session_factory()
    try:
        concept = Concept(user_id=user_id, name="self-attention", description="Attention over one sequence")
        db.add(concept)
        db.commit()
        db.refresh(concept)

        card = ReviewCard(
            user_id=user_id,
            concept_id=concept.id,
            question=question,
            answer="A mechanism relating positions within a single sequence.",
        )
        db.add(card)
        db.commit()
        db.refresh(card)
        return card.id
    finally:
        db.close()


def _user_id_from_headers(headers: dict) -> int:
    token = headers["Authorization"].split(" ")[1]
    return int(decode_access_token(token))


def test_due_cards_empty_for_new_user(client, auth_headers):
    resp = client.get("/api/v1/review/due", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_new_card_is_immediately_due(client, auth_headers):
    user_id = _user_id_from_headers(auth_headers)
    card_id = _seed_review_card(client, user_id)

    resp = client.get("/api/v1/review/due", headers=auth_headers)
    assert resp.status_code == 200
    due_ids = [c["id"] for c in resp.json()]
    assert card_id in due_ids


def test_grading_a_card_reschedules_it_and_removes_from_due_list(client, auth_headers):
    user_id = _user_id_from_headers(auth_headers)
    card_id = _seed_review_card(client, user_id)

    resp = client.post(f"/api/v1/review/{card_id}/grade", headers=auth_headers, json={"quality": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body["repetitions"] == 1
    assert body["interval_days"] == 1

    # A card scheduled 1 day out should no longer appear in "due now"
    resp = client.get("/api/v1/review/due", headers=auth_headers)
    due_ids = [c["id"] for c in resp.json()]
    assert card_id not in due_ids


def test_grade_invalid_quality_rejected(client, auth_headers):
    user_id = _user_id_from_headers(auth_headers)
    card_id = _seed_review_card(client, user_id)

    resp = client.post(f"/api/v1/review/{card_id}/grade", headers=auth_headers, json={"quality": 9})
    assert resp.status_code == 422  # pydantic field validation (le=5)


def test_cannot_grade_another_users_card(client, auth_headers):
    user_id = _user_id_from_headers(auth_headers)
    card_id = _seed_review_card(client, user_id)

    other = client.post(
        "/api/v1/auth/register",
        json={"email": "other@b.com", "password": "somepassword123", "full_name": "Other"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}

    resp = client.post(f"/api/v1/review/{card_id}/grade", headers=other_headers, json={"quality": 5})
    assert resp.status_code == 404
