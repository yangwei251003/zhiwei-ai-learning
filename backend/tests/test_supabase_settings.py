from app.core import Settings


def test_settings_enable_supabase_rag_and_storage():
    settings = Settings(
        secret_key="test-secret",
        rag_backend="supabase",
        supabase_url="https://project.supabase.co",
        supabase_service_role_key="service-secret",
        supabase_storage_bucket="knowledge-uploads",
    )

    assert settings.uses_supabase_rag is True
