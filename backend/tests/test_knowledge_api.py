import hashlib
import inspect
from pathlib import Path
from uuid import uuid4

import pytest
from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class DeterministicEmbedding:
    def encode(self, texts):
        return [
            [byte / 255 for byte in hashlib.sha256(text.lower().encode()).digest()[:8]]
            for text in texts
        ]


class Summary:
    def summarize(self, text):
        return {"summary": text[:30], "keywords": ["network"]}


class BrokenSummary:
    def summarize(self, text):
        raise RuntimeError("offline")


@pytest.fixture
def knowledge_client(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "knowledge-secret")
    from app.core import get_settings

    get_settings.cache_clear()
    from app.api.knowledge import get_knowledge_service
    from app.core.database import Base, get_db
    from app.knowledge_base.store import ChromaRAGStore
    from app.main import app
    from app.services.knowledge_service import KnowledgeService

    engine = create_engine(
        f"sqlite:///{(tmp_path / 'api.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(engine)
    store = ChromaRAGStore(tmp_path / "chroma", DeterministicEmbedding())
    uploads = tmp_path / "uploads"
    service = KnowledgeService(store, uploads, Summary())

    def override_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_knowledge_service] = lambda: service
    try:
        with TestClient(app) as client:
            yield client, service, uploads
    finally:
        app.dependency_overrides.clear()
        service.close()
        engine.dispose()
        get_settings.cache_clear()


def _register(client):
    response = client.post(
        "/api/auth/register",
        json={"username": f"kb-{uuid4().hex[:8]}", "password": "secret123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _pdf_bytes(text: str) -> bytes:
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(data)
    data.extend(b"xref\n0 5\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(data)


def _format_payload(tmp_path: Path, extension: str) -> tuple[bytes, str]:
    if extension == ".pdf":
        return _pdf_bytes("Neural network"), "application/pdf"
    if extension == ".docx":
        path = tmp_path / "fixture.docx"
        document = Document()
        document.add_paragraph("Neural network")
        document.save(path)
        return path.read_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if extension == ".md":
        return b"# Neural network", "text/markdown"
    return b"Neural network", "text/plain"


def test_knowledge_endpoints_require_jwt(knowledge_client):
    client, _, _ = knowledge_client
    assert client.get("/api/knowledge/list").status_code == 401
    assert client.post("/api/knowledge/search", json={"query": "x", "course": "AI"}).status_code == 401


def test_knowledge_endpoints_are_sync_session_work_units():
    from app.api import knowledge

    endpoints = [
        knowledge.upload_knowledge, knowledge.list_knowledge, knowledge.search_knowledge,
        knowledge.get_document, knowledge.delete_document, knowledge.reindex_document,
    ]
    assert all(not inspect.iscoroutinefunction(endpoint) for endpoint in endpoints)


@pytest.mark.parametrize("extension", [".pdf", ".docx", ".txt", ".md"])
def test_api_uploads_each_supported_format(knowledge_client, tmp_path, extension):
    client, _, _ = knowledge_client
    headers = _register(client)
    data, mime = _format_payload(tmp_path, extension)
    response = client.post(
        "/api/knowledge/upload", headers=headers, data={"course": "AI"},
        files={"file": (f"lesson{extension}", data, mime)},
    )
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "indexed"


def test_upload_search_reindex_ownership_and_delete(knowledge_client):
    client, _, uploads = knowledge_client
    owner = _register(client)
    stranger = _register(client)
    response = client.post(
        "/api/knowledge/upload",
        headers=owner,
        data={"course": "AI"},
        files={"file": ("../private.txt", b"Neural network and attention", "text/plain")},
    )
    assert response.status_code == 201, response.text
    document = response.json()
    assert document["status"] == "indexed"
    assert document["summary"]
    assert document["keywords"] == ["network"]
    assert document["chunk_count"] == 1
    assert document["original_filename"] == "private.txt"
    stored = list(uploads.iterdir())
    assert len(stored) == 1 and stored[0].name != "private.txt"

    search = client.post(
        "/api/knowledge/search",
        headers=owner,
        json={"query": "network", "course": "AI", "top_k": 5},
    )
    assert search.status_code == 200
    assert search.json()[0]["highlight_spans"] == [{"start": 7, "end": 14}]
    assert client.get(f"/api/knowledge/{document['id']}", headers=stranger).status_code == 404
    assert client.delete(f"/api/knowledge/{document['id']}", headers=stranger).status_code == 404

    assert client.post(f"/api/knowledge/{document['id']}/reindex", headers=owner).status_code == 200
    assert len(client.post(
        "/api/knowledge/search", headers=owner,
        json={"query": "network", "course": "AI", "top_k": 20},
    ).json()) == 1
    assert client.delete(f"/api/knowledge/{document['id']}", headers=owner).status_code == 204
    assert not stored[0].exists()


def test_upload_rejects_mime_spoof_and_invalid_top_k(knowledge_client):
    client, _, _ = knowledge_client
    headers = _register(client)
    spoof = client.post(
        "/api/knowledge/upload", headers=headers, data={"course": "AI"},
        files={"file": ("notes.txt", b"plain", "application/pdf")},
    )
    assert spoof.status_code == 400
    invalid = client.post(
        "/api/knowledge/search", headers=headers,
        json={"query": "network", "course": "AI", "top_k": 21},
    )
    assert invalid.status_code == 422


def test_upload_rejects_oversized_file(knowledge_client):
    from app.knowledge_base.loaders import MAX_FILE_BYTES

    client, _, _ = knowledge_client
    headers = _register(client)
    response = client.post(
        "/api/knowledge/upload", headers=headers, data={"course": "AI"},
        files={"file": ("huge.txt", b"x" * (MAX_FILE_BYTES + 1), "text/plain")},
    )
    assert response.status_code == 413


def test_summary_failure_keeps_searchable_index(knowledge_client):
    client, service, _ = knowledge_client
    service.summarizer = BrokenSummary()
    headers = _register(client)
    uploaded = client.post(
        "/api/knowledge/upload", headers=headers, data={"course": "AI"},
        files={"file": ("notes.md", b"# Neural network", "text/markdown")},
    )
    assert uploaded.status_code == 201
    assert uploaded.json()["status"] == "indexed_with_metadata_error"
    found = client.post(
        "/api/knowledge/search", headers=headers,
        json={"query": "Neural", "course": "AI"},
    )
    assert found.status_code == 200 and len(found.json()) == 1


def test_reindex_parse_failure_removes_previously_indexed_vectors(knowledge_client):
    client, service, uploads = knowledge_client
    headers = _register(client)
    uploaded = client.post(
        "/api/knowledge/upload", headers=headers, data={"course": "AI"},
        files={"file": ("notes.txt", b"Neural network", "text/plain")},
    )
    assert uploaded.status_code == 201
    document_id = uploaded.json()["id"]
    assert client.post(
        "/api/knowledge/search", headers=headers,
        json={"query": "Neural", "course": "AI"},
    ).json()

    next(uploads.iterdir()).write_bytes(b"%PDF-fake")
    failed = client.post(f"/api/knowledge/{document_id}/reindex", headers=headers)

    assert failed.status_code == 400
    assert service.store.count_document(1, document_id) == 0
    assert client.post(
        "/api/knowledge/search", headers=headers,
        json={"query": "Neural", "course": "AI"},
    ).json() == []
    detail = client.get(f"/api/knowledge/{document_id}", headers=headers)
    assert detail.json()["status"] == "failed"


def test_reindex_missing_storage_removes_previously_indexed_vectors(knowledge_client):
    client, service, uploads = knowledge_client
    headers = _register(client)
    uploaded = client.post(
        "/api/knowledge/upload", headers=headers, data={"course": "AI"},
        files={"file": ("notes.txt", b"Neural network", "text/plain")},
    )
    assert uploaded.status_code == 201
    document_id = uploaded.json()["id"]
    assert client.post(
        "/api/knowledge/search", headers=headers,
        json={"query": "Neural", "course": "AI"},
    ).json()

    next(uploads.iterdir()).unlink()
    failed = client.post(f"/api/knowledge/{document_id}/reindex", headers=headers)

    assert failed.status_code == 503
    assert service.store.count_document(1, document_id) == 0
    assert client.post(
        "/api/knowledge/search", headers=headers,
        json={"query": "Neural", "course": "AI"},
    ).json() == []
    detail = client.get(f"/api/knowledge/{document_id}", headers=headers)
    assert detail.json()["status"] == "failed"


def test_delete_store_failure_is_retryable_and_never_looks_indexed(knowledge_client, monkeypatch):
    client, service, _ = knowledge_client
    headers = _register(client)
    uploaded = client.post(
        "/api/knowledge/upload", headers=headers, data={"course": "AI"},
        files={"file": ("notes.txt", b"Neural network", "text/plain")},
    ).json()
    original_delete = service.store.delete_document
    monkeypatch.setattr(service.store, "delete_document", lambda *args: (_ for _ in ()).throw(RuntimeError("store down")))

    failed = client.delete(f"/api/knowledge/{uploaded['id']}", headers=headers)

    assert failed.status_code == 503
    assert client.get(f"/api/knowledge/{uploaded['id']}", headers=headers).json()["status"] == "delete_failed"
    monkeypatch.setattr(service.store, "delete_document", original_delete)
    assert client.delete(f"/api/knowledge/{uploaded['id']}", headers=headers).status_code == 204


def test_delete_unlink_failure_is_retryable_and_never_looks_indexed(knowledge_client, monkeypatch):
    client, _, uploads = knowledge_client
    headers = _register(client)
    uploaded = client.post(
        "/api/knowledge/upload", headers=headers, data={"course": "AI"},
        files={"file": ("notes.txt", b"Neural network", "text/plain")},
    ).json()
    stored = next(uploads.iterdir())
    original_unlink = Path.unlink
    failed_once = False

    def flaky_unlink(path, *args, **kwargs):
        nonlocal failed_once
        if path == stored and not failed_once:
            failed_once = True
            raise PermissionError("file busy")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", flaky_unlink)
    failed = client.delete(f"/api/knowledge/{uploaded['id']}", headers=headers)

    assert failed.status_code == 503
    assert client.get(f"/api/knowledge/{uploaded['id']}", headers=headers).json()["status"] == "delete_failed"
    assert client.delete(f"/api/knowledge/{uploaded['id']}", headers=headers).status_code == 204
