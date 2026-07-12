"""Private Supabase Storage client used by the stateless knowledge service."""

from __future__ import annotations

from typing import Protocol
from urllib.parse import quote

import httpx


class StorageError(RuntimeError):
    """Raised when Supabase Storage rejects an object operation."""


class StorageClient(Protocol):
    def upload(self, path: str, content: bytes, mime: str) -> None: ...
    def download(self, path: str) -> bytes: ...
    def delete(self, path: str) -> None: ...


class SupabaseStorage:
    def __init__(
        self,
        base_url: str,
        service_role_key: str,
        bucket: str,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.bucket = bucket
        self._headers = {
            "Authorization": f"Bearer {service_role_key}",
            "apikey": service_role_key,
        }
        self._client = httpx.Client(timeout=30.0, transport=transport)

    def _url(self, path: str) -> str:
        safe_path = quote(path.strip("/"), safe="/")
        return f"{self.base_url}/storage/v1/object/{quote(self.bucket, safe='')}/{safe_path}"

    @staticmethod
    def _ensure_success(response: httpx.Response, operation: str) -> None:
        if response.is_success:
            return
        raise StorageError(f"Supabase Storage {operation} failed ({response.status_code})")

    def upload(self, path: str, content: bytes, mime: str) -> None:
        response = self._client.post(
            self._url(path),
            content=content,
            headers={**self._headers, "Content-Type": mime, "x-upsert": "true"},
        )
        self._ensure_success(response, "upload")

    def download(self, path: str) -> bytes:
        response = self._client.get(self._url(path), headers=self._headers)
        self._ensure_success(response, "download")
        return response.content

    def delete(self, path: str) -> None:
        response = self._client.delete(self._url(path), headers=self._headers)
        self._ensure_success(response, "delete")

    def close(self) -> None:
        self._client.close()
