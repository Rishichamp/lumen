import shutil
import tempfile

import pytest

from app.services.embedding_service import DeterministicHashEmbedder, VectorIndexStore


@pytest.fixture
def temp_index_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_deterministic_embedder_is_stable_and_normalized():
    embedder = DeterministicHashEmbedder(dim=64)
    v1 = embedder.embed(["hello world"])
    v2 = embedder.embed(["hello world"])
    assert (v1 == v2).all()
    assert abs(float((v1[0] ** 2).sum()) - 1.0) < 1e-5  # L2-normalized


def test_deterministic_embedder_distinguishes_different_text():
    embedder = DeterministicHashEmbedder(dim=64)
    v1 = embedder.embed(["transformers attention mechanism"])
    v2 = embedder.embed(["completely unrelated cooking recipe"])
    similarity = float((v1[0] * v2[0]).sum())
    assert similarity < 0.9  # not identical vectors


def test_vector_index_store_add_and_search_roundtrip(temp_index_dir):
    store = VectorIndexStore(index_dir=temp_index_dir, dim=64)
    embedder = DeterministicHashEmbedder(dim=64)

    texts = ["gradient descent optimizes loss", "transformers use self attention", "cats are mammals"]
    vectors = embedder.embed(texts)
    start_row = store.add(user_id=1, vectors=vectors)
    assert start_row == 0

    query_vector = embedder.embed(["self attention in transformers"])[0]
    row_ids, scores = store.search(user_id=1, query_vector=query_vector, top_k=2)

    assert len(row_ids) == 2
    assert 1 in row_ids  # "transformers use self attention" should be the closest match
    assert scores[row_ids.index(1)] == max(scores)


def test_vector_index_store_isolates_users(temp_index_dir):
    store = VectorIndexStore(index_dir=temp_index_dir, dim=64)
    embedder = DeterministicHashEmbedder(dim=64)

    store.add(user_id=1, vectors=embedder.embed(["user one paper content"]))
    row_ids, _ = store.search(user_id=2, query_vector=embedder.embed(["anything"])[0], top_k=5)
    assert row_ids == []  # user 2 has no index yet


def test_vector_index_store_delete_removes_file(temp_index_dir):
    store = VectorIndexStore(index_dir=temp_index_dir, dim=64)
    embedder = DeterministicHashEmbedder(dim=64)
    store.add(user_id=5, vectors=embedder.embed(["some text"]))

    store.delete_user_index(user_id=5)
    row_ids, _ = store.search(user_id=5, query_vector=embedder.embed(["x"])[0], top_k=1)
    assert row_ids == []
