from app.models import KnowledgeChunk


def test_knowledge_chunk_has_tenant_document_and_vector_fields():
    names = {column.name for column in KnowledgeChunk.__table__.columns}

    assert {"user_id", "document_id", "course", "content", "embedding", "search_vector"} <= names
