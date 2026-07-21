import time


def test_health_check(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_login_and_me(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "a@b.com", "password": "somepassword123", "full_name": "A B"},
    )
    assert resp.status_code == 201
    token = resp.json()["access_token"]

    resp = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "somepassword123"})
    assert resp.status_code == 200

    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "a@b.com"


def test_register_duplicate_email_rejected(client):
    payload = {"email": "dupe@b.com", "password": "somepassword123", "full_name": "Dup"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409


def test_unauthenticated_request_rejected(client):
    resp = client.get("/api/v1/papers")
    assert resp.status_code == 401


def test_upload_ingest_search_and_chat_full_flow(client, auth_headers, sample_pdf_bytes):
    # 1. Upload a paper
    resp = client.post(
        "/api/v1/papers",
        headers=auth_headers,
        files={"file": ("attention.pdf", sample_pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 201, resp.text
    paper_id = resp.json()["id"]
    assert resp.json()["status"] == "processing"

    # 2. Wait for the background ingestion task to finish (bounded poll,
    # not a fixed sleep, so the test stays fast on faster machines and
    # doesn't flake on slower ones).
    for _ in range(50):
        resp = client.get(f"/api/v1/papers/{paper_id}", headers=auth_headers)
        if resp.json()["status"] in ("ready", "failed"):
            break
        time.sleep(0.1)
    assert resp.json()["status"] == "ready", resp.json()

    # 3. Library listing shows it
    resp = client.get("/api/v1/papers", headers=auth_headers)
    assert resp.status_code == 200
    assert any(p["id"] == paper_id for p in resp.json())

    # 4. Semantic search finds the ingested content
    resp = client.get("/api/v1/search", headers=auth_headers, params={"q": "self attention mechanism"})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) > 0
    assert results[0]["paper_id"] == paper_id

    # 5. RAG chat answers grounded in the retrieved chunk, with citations
    resp = client.post(
        "/api/v1/chat",
        headers=auth_headers,
        json={"message": "What architecture does this paper propose?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["citations"], "expected at least one citation from the ingested paper"
    assert body["citations"][0]["paper_id"] == paper_id

    # 6. Message history persisted
    resp = client.get(f"/api/v1/chat/sessions/{body['session_id']}/messages", headers=auth_headers)
    assert resp.status_code == 200
    roles = [m["role"] for m in resp.json()]
    assert roles == ["user", "assistant"]


def test_paper_not_found_for_other_user(client, sample_pdf_bytes):
    # user A uploads
    reg_a = client.post(
        "/api/v1/auth/register",
        json={"email": "usera@b.com", "password": "somepassword123", "full_name": "User A"},
    )
    headers_a = {"Authorization": f"Bearer {reg_a.json()['access_token']}"}
    upload = client.post(
        "/api/v1/papers", headers=headers_a,
        files={"file": ("p.pdf", sample_pdf_bytes, "application/pdf")},
    )
    paper_id = upload.json()["id"]

    # user B cannot access it
    reg_b = client.post(
        "/api/v1/auth/register",
        json={"email": "userb@b.com", "password": "somepassword123", "full_name": "User B"},
    )
    headers_b = {"Authorization": f"Bearer {reg_b.json()['access_token']}"}
    resp = client.get(f"/api/v1/papers/{paper_id}", headers=headers_b)
    assert resp.status_code == 404


def test_upload_rejects_non_pdf(client, auth_headers):
    resp = client.post(
        "/api/v1/papers", headers=auth_headers,
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400
