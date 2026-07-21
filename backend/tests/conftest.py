"""
Shared test fixtures.

Uses FastAPI's `dependency_overrides` to point `get_db` at an isolated,
per-test SQLite file, and monkeypatches the production
`SentenceTransformerEmbedder` with the dependency-free
`DeterministicHashEmbedder` at the module level of each route module.
This exercises the full HTTP request -> ingest -> retrieve -> chat
pipeline in CI without downloading model weights or calling an external
LLM API (see docs/TESTING.md).

Note: an earlier version of this fixture used importlib.reload() to
re-apply env-var-driven settings, which silently broke SQLAlchemy model
registration (reloading app.db.database creates a *new* declarative
Base class, orphaning the metadata that app.models.models already
registered against the original Base — resulting in "no such table"
errors). Dependency overrides avoid the problem entirely and are the
pattern FastAPI's own docs recommend for this reason.
"""
import os
import shutil
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.database import Base, get_db
from app.services.embedding_service import DeterministicHashEmbedder, VectorIndexStore


@pytest.fixture(scope="function")
def client(monkeypatch):
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test.db")
    upload_dir = os.path.join(tmp_dir, "uploads")
    index_dir = os.path.join(tmp_dir, "indexes")
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(index_dir, exist_ok=True)

    settings = get_settings()
    monkeypatch.setattr(settings, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(settings, "VECTOR_INDEX_DIR", index_dir)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(settings, "ENV", "test")

    test_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    def _override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    import app.api.routes.papers as papers_module
    import app.api.routes.chat as chat_module
    import app.api.routes.search as search_module
    import app.main as main_module

    test_index_store = VectorIndexStore(index_dir, dim=384)
    test_embedder = DeterministicHashEmbedder(dim=384)

    monkeypatch.setattr(papers_module, "SentenceTransformerEmbedder", DeterministicHashEmbedder)
    monkeypatch.setattr(papers_module, "_index_store", test_index_store)
    monkeypatch.setattr(papers_module, "_session_factory", TestSessionLocal)
    monkeypatch.setattr(chat_module, "_embedder", test_embedder)
    monkeypatch.setattr(chat_module, "_index_store", test_index_store)
    monkeypatch.setattr(search_module, "_embedder", test_embedder)
    monkeypatch.setattr(search_module, "_index_store", test_index_store)

    main_module.app.dependency_overrides[get_db] = _override_get_db

    with TestClient(main_module.app) as test_client:
        test_client.db_session_factory = TestSessionLocal  # exposed for tests that need to seed data directly
        yield test_client

    main_module.app.dependency_overrides.clear()
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def auth_headers(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "student@iitism.ac.in", "password": "researchpass123", "full_name": "Test Student"},
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(
        0, 10,
        "Attention Is All You Need\n\n"
        "Abstract: We propose the Transformer, a novel neural network architecture "
        "based solely on attention mechanisms, dispensing with recurrence and "
        "convolutions entirely. The Transformer achieves superior quality on "
        "machine translation tasks while being more parallelizable and requiring "
        "significantly less time to train. Self-attention allows the model to "
        "relate different positions of a single sequence to compute a representation.",
    )
    return bytes(pdf.output())
