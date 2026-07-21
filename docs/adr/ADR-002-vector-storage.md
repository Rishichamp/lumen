# ADR-002: Per-user FAISS indexes over a hosted vector database

## Status
Accepted (v1). Migration path to Qdrant documented below.

## Context
Every user's paper library needs a vector index for semantic
retrieval. Candidates considered: Qdrant (self-hosted or cloud),
Pinecone (managed SaaS), pgvector (Postgres extension), and FAISS
(in-process library).

## Decision
One FAISS `IndexFlatIP` file per user, stored on a persistent volume,
loaded/queried through the `VectorIndexStore` class in
`app/services/embedding_service.py`.

## Rationale
- **Scale fit**: a single user's library tops out at a few thousand
  chunks. `IndexFlatIP` (exact, brute-force cosine similarity via
  normalized dot product) is fast enough at this size — no need for
  the approximate-nearest-neighbor indexes (HNSW, IVF) that justify a
  dedicated vector DB at millions-of-vectors scale.
- **Isolation by construction**: one file per user means there is no
  possibility of a query leaking another user's vectors through a
  missed `WHERE user_id = ?filter` — the isolation is structural, not
  a runtime check that can be forgotten in a new endpoint.
- **Zero network hop, zero extra infra**: no separate service to
  deploy, monitor, or pay for at this stage.
- **Trivial data deletion**: deleting a user's account is `rm` one
  file — relevant for GDPR-style "right to erasure" requirements.

## Known limitation (accepted for v1)
`IndexFlatIP` doesn't support cheap row deletion. Deleting a paper
leaves its vectors in the index as unreachable dead weight (the SQL
`Chunk` rows are deleted, so they're never returned to the API, but
the FAISS file doesn't shrink). A periodic compaction job — rebuild
the index from the chunks that still exist in Postgres — is the
planned fix; tracked in the product roadmap, not yet built.

## Migration path to Qdrant
Triggered by: (a) a "shared corpus" feature where multiple users query
overlapping vectors (breaks the one-file-per-user isolation model), or
(b) any single user's library exceeding ~50k chunks where brute-force
search starts costing noticeable query latency.

`VectorIndexStore` is the seam: it exposes `add`, `search`, and
`delete_user_index`. A `QdrantVectorIndexStore` implementing the same
three methods against Qdrant's client is a drop-in replacement —
nothing in `rag_service.py` or the route handlers needs to change.
