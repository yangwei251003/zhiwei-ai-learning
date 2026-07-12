from types import SimpleNamespace


def test_knowledge_service_uses_supabase_adapters_when_configured(monkeypatch):
    from app.api import knowledge
    from app.knowledge_base.supabase_store import SupabaseRAGStore
    from app.knowledge_base.supabase_storage import SupabaseStorage

    settings = SimpleNamespace(
        uses_supabase_rag=True,
        embedding_model="offline-model",
        supabase_url="https://project.supabase.co",
        supabase_service_role_key="service-secret",
        supabase_storage_bucket="knowledge-uploads",
        knowledge_upload_dir="./temporary-uploads",
    )
    monkeypatch.setattr(knowledge, "get_settings", lambda: settings)
    monkeypatch.setattr(knowledge, "LLMDocumentSummarizer", lambda: object())
    knowledge.get_knowledge_service.cache_clear()

    service = knowledge.get_knowledge_service()

    assert isinstance(service.store, SupabaseRAGStore)
    assert isinstance(service.object_storage, SupabaseStorage)
    service.close()
    knowledge.get_knowledge_service.cache_clear()
