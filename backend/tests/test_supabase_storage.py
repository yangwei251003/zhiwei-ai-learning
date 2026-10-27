import httpx

from app.knowledge_base.supabase_storage import SupabaseStorage


def test_upload_uses_private_bucket_and_service_role():
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["authorization"] = request.headers["authorization"]
        seen["apikey"] = request.headers["apikey"]
        return httpx.Response(200)

    storage = SupabaseStorage(
        "https://project.supabase.co",
        "service-secret",
        "knowledge-uploads",
        transport=httpx.MockTransport(handler),
    )

    storage.upload("7/file.pdf", b"pdf", "application/pdf")

    assert seen["url"].endswith("/storage/v1/object/knowledge-uploads/7/file.pdf")
    assert seen["authorization"] == "Bearer service-secret"
    assert seen["apikey"] == "service-secret"
