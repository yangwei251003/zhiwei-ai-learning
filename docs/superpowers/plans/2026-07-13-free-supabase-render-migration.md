# Free Supabase + Render Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace local Chroma and upload persistence with Supabase pgvector and Storage, so the FastAPI service can run statelessly on Render free.

**Architecture:** A Supabase Storage adapter owns private file objects. A SQLAlchemy-backed RAG store owns tenant-filtered chunk rows and ranks by pgvector cosine distance, with lexical search as a safe fallback. Vercel serves the frontend and Render runs FastAPI without a disk.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL/Supabase, pgvector, Supabase Storage REST API, Vue/Vite, pytest, Vitest.

---

### Task 1: Add Supabase settings

**Files:** Modify `backend/app/core/__init__.py`, `backend/.env.example`; create `backend/tests/test_supabase_settings.py`.

- [ ] Write the failing test:

```python
from app.core import Settings

def test_settings_enable_supabase_rag_and_storage():
    settings = Settings(secret_key="test-secret", rag_backend="supabase", supabase_url="https://project.supabase.co", supabase_service_role_key="service-secret")
    assert settings.uses_supabase_rag is True
```

- [ ] Run `python -m pytest tests/test_supabase_settings.py -q`; expect a missing-setting failure.
- [ ] Add `RAG_BACKEND`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_STORAGE_BUCKET`, validation, and `uses_supabase_rag`.
- [ ] Re-run the test; expect PASS.
- [ ] Commit: `feat: configure Supabase knowledge backend`.

### Task 2: Add private Storage adapter

**Files:** Create `backend/app/knowledge_base/supabase_storage.py`, `backend/tests/test_supabase_storage.py`; modify `backend/requirements.txt`.

- [ ] Write the failing test:

```python
async def test_upload_uses_private_bucket_and_service_role():
    storage = SupabaseStorage("https://project.supabase.co", "service-secret", "knowledge-uploads", transport=mock_transport)
    await storage.upload("7/file.pdf", b"pdf", "application/pdf")
    assert seen_url.endswith("/storage/v1/object/knowledge-uploads/7/file.pdf")
    assert seen_authorization == "Bearer service-secret"
```

- [ ] Run `python -m pytest tests/test_supabase_storage.py -q`; expect an import failure.
- [ ] Implement async `upload`, `download`, and `delete` with URL-encoded paths, `Authorization` and `apikey` headers, and explicit non-2xx errors.
- [ ] Re-run the test; expect PASS.
- [ ] Commit: `feat: add private Supabase storage adapter`.

### Task 3: Add pgvector chunk schema

**Files:** Modify `backend/app/models/__init__.py`, `backend/requirements.txt`; create Alembic revision, `backend/tests/test_pgvector_schema.py`.

- [ ] Write the failing test:

```python
def test_knowledge_chunk_has_tenant_document_and_vector_fields():
    names = {column.name for column in KnowledgeChunk.__table__.columns}
    assert {"user_id", "document_id", "course", "content", "embedding", "search_vector"} <= names
```

- [ ] Run `python -m pytest tests/test_pgvector_schema.py -q`; expect `KnowledgeChunk` import failure.
- [ ] Add a 384-dimensional vector column, PostgreSQL `TSVECTOR`, tenant/document uniqueness and indexes. Migration must run `CREATE EXTENSION IF NOT EXISTS vector` and stay importable under SQLite tests.
- [ ] Re-run the test; expect PASS.
- [ ] Commit: `feat: add pgvector knowledge chunk schema`.

### Task 4: Add Supabase RAG and fallback

**Files:** Create `backend/app/knowledge_base/supabase_store.py`, `backend/tests/test_supabase_rag_store.py`; modify `backend/app/api/knowledge.py`.

- [ ] Write the failing test:

```python
def test_store_returns_tenant_scoped_lexical_hit_when_embedding_fails(session):
    store = SupabaseRAGStore(session, FailingEmbedding())
    store.index_document(1, 4, "Python", "variables.pdf", [chunk("Python variable")])
    assert store.search("Python variable", 1, "Python")[0]["citation_id"] == "4:0"
```

- [ ] Run `python -m pytest tests/test_supabase_rag_store.py -q`; expect import failure.
- [ ] Implement `index_document`, `delete_document`, `count_document`, and `search` matching `ChromaRAGStore`'s response shape. Filter by user and course before pgvector ranking; on unavailable embeddings use lexical matching with the same tenant filter.
- [ ] Re-run the test; expect PASS.
- [ ] Commit: `feat: add Supabase pgvector retrieval`.

### Task 5: Move document lifecycle to Storage

**Files:** Modify `backend/app/services/knowledge_service.py` and `backend/app/api/knowledge.py`; modify `backend/tests/test_knowledge_api.py`.

- [ ] Write the failing test asserting `DELETE /api/knowledge/{id}` deletes its private object path.
- [ ] Run `python -m pytest tests/test_knowledge_api.py -q`; expect failure because deletion only handles local files.
- [ ] Add a storage protocol; production uploads bytes to Supabase, parsing uses a request-local temporary file, and document deletion removes the Storage object plus chunk rows.
- [ ] Re-run the test; expect PASS.
- [ ] Commit: `feat: persist knowledge documents in Supabase Storage`.

### Task 6: Make deployment stateless

**Files:** Modify `backend/render.yaml`, `backend/.env.example`, `frontend/.env.example`; create `backend/Dockerfile`, `backend/tests/test_deployment_manifest.py`.

- [ ] Write the failing test:

```python
def test_render_manifest_does_not_require_a_persistent_disk():
    manifest = Path("render.yaml").read_text(encoding="utf-8")
    assert "disk:" not in manifest
    assert "RAG_BACKEND" in manifest
```

- [ ] Run `python -m pytest tests/test_deployment_manifest.py -q`; expect failure because the manifest configures a disk.
- [ ] Remove the disk, add Supabase secret placeholders and `RAG_BACKEND=supabase`, and add a Dockerfile that preloads the embedding model at build time.
- [ ] Re-run the test; expect PASS.
- [ ] Commit: `feat: configure free stateless deployment`.

### Task 7: Verify and deploy

**Files:** Modify `documents/测试报告.md`; create `documents/上线部署说明.md`.

- [ ] Run `python -m pytest -q`, `npm test -- --run`, and `npm run build`; expect all PASS.
- [ ] In Supabase, enable `vector` and create private bucket `knowledge-uploads`.
- [ ] In Render, create the free service, enter private secrets only in its dashboard, deploy, and verify `/health`.
- [ ] In Vercel, deploy `frontend`, set `VITE_API_BASE_URL`, set final Render `CORS_ORIGINS`, and redeploy.
- [ ] Publicly verify registration, SSE, upload/retrieval, path generation, refresh, and cold-start reconnect; record URLs and limits.
- [ ] Commit: `docs: record public deployment verification`.
