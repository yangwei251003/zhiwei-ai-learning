from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile

from docx import Document
from pypdf import PdfReader


class DocumentParseError(ValueError):
    """Raised when an uploaded document cannot be parsed safely."""


ALLOWED_CONTENT_TYPES = {
    ".txt": {"text/plain", "application/octet-stream"},
    ".md": {"text/markdown", "text/plain", "application/octet-stream"},
    ".markdown": {"text/markdown", "text/plain", "application/octet-stream"},
    ".pdf": {"application/pdf", "application/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
}


def validate_document_upload(
    filename: str,
    content_type: str,
    payload: bytes,
    *,
    max_docx_entries: int = 2_000,
    max_docx_uncompressed_bytes: int = 100 * 1024 * 1024,
) -> None:
    suffix = Path(filename).suffix.lower()
    allowed_types = ALLOWED_CONTENT_TYPES.get(suffix)
    if allowed_types is None:
        raise DocumentParseError(f"不支持的文档格式：{suffix or '无扩展名'}")
    if not payload:
        raise DocumentParseError("上传文件不能为空")
    normalized_type = (
        (content_type or "application/octet-stream").split(";", 1)[0].strip().lower()
    )
    if normalized_type not in allowed_types:
        raise DocumentParseError("文件扩展名与声明类型不匹配")
    if suffix == ".pdf" and not payload.startswith(b"%PDF-"):
        raise DocumentParseError("PDF 文件签名无效")
    if suffix == ".docx":
        if not payload.startswith(b"PK\x03\x04"):
            raise DocumentParseError("DOCX 文件签名无效")
        try:
            with ZipFile(BytesIO(payload)) as archive:
                entries = archive.infolist()
                names = {entry.filename for entry in entries}
                if len(entries) > max_docx_entries:
                    raise DocumentParseError("DOCX 压缩包条目过多")
                if (
                    sum(entry.file_size for entry in entries)
                    > max_docx_uncompressed_bytes
                ):
                    raise DocumentParseError("DOCX 解压后内容超过安全限制")
                if any(entry.flag_bits & 0x1 for entry in entries):
                    raise DocumentParseError("不支持加密 DOCX")
                if not {"[Content_Types].xml", "word/document.xml"}.issubset(names):
                    raise DocumentParseError("DOCX 文件结构无效")
        except BadZipFile as exc:
            raise DocumentParseError("DOCX 文件签名无效") from exc
    if suffix in {".txt", ".md", ".markdown"} and b"\x00" in payload:
        raise DocumentParseError("文本文件包含不允许的二进制内容")


@dataclass(frozen=True)
class ParsedSection:
    text: str
    metadata: dict[str, Any]


def parse_document(filename: str, payload: bytes) -> list[ParsedSection]:
    suffix = Path(filename).suffix.lower()
    try:
        if suffix in {".txt", ".md", ".markdown"}:
            return _parse_text(filename, payload)
        if suffix == ".docx":
            return _parse_docx(filename, payload)
        if suffix == ".pdf":
            return _parse_pdf(filename, payload)
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError(f"无法解析文档 {filename}") from exc
    raise DocumentParseError(f"不支持的文档格式：{suffix or '无扩展名'}")


def _parse_text(filename: str, payload: bytes) -> list[ParsedSection]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DocumentParseError("文本文件必须使用 UTF-8 编码") from exc
    text = text.strip()
    return [ParsedSection(text, {"source": filename})] if text else []


def _parse_docx(filename: str, payload: bytes) -> list[ParsedSection]:
    document = Document(BytesIO(payload))
    return [
        ParsedSection(
            paragraph.text.strip(),
            {"source": filename, "paragraph": position},
        )
        for position, paragraph in enumerate(document.paragraphs, start=1)
        if paragraph.text.strip()
    ]


def _parse_pdf(filename: str, payload: bytes) -> list[ParsedSection]:
    reader = PdfReader(BytesIO(payload))
    sections: list[ParsedSection] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            sections.append(
                ParsedSection(text, {"source": filename, "page": page_number})
            )
    return sections


def chunk_sections(
    sections: list[ParsedSection], chunk_size: int = 800, overlap: int = 120
) -> list[ParsedSection]:
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须是正整数")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap 必须大于等于 0 且小于 chunk_size")

    chunks: list[ParsedSection] = []
    step = chunk_size - overlap
    for section in sections:
        text = section.text.strip()
        if not text:
            continue
        for start in range(0, len(text), step):
            content = text[start : start + chunk_size]
            if not content:
                break
            metadata = {**section.metadata, "chunk_index": len(chunks)}
            chunks.append(ParsedSection(content, metadata))
            if start + chunk_size >= len(text):
                break
    return chunks
