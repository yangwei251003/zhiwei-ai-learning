"""Parse supported documents into text segments with source positions."""

from dataclasses import dataclass
from io import BufferedReader
from pathlib import Path
import zipfile

from docx import Document
from pypdf import PdfReader


class DocumentParseError(ValueError):
    """Raised when a document is unsupported or cannot yield usable text."""


MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_DOCX_MEMBERS = 10_000
MAX_DOCX_MEMBER_BYTES = 50 * 1024 * 1024
MAX_DOCX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_DOCX_COMPRESSION_RATIO = 100
MAX_PDF_PAGES = 2_000
MAX_PDF_EXTRACTED_CHARS = 10_000_000


@dataclass(frozen=True, slots=True)
class TextSegment:
    text: str
    source_type: str
    page: int | None = None
    paragraph: int | None = None
    char_start: int = 0
    char_end: int = 0


_MIME_EXTENSIONS = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
    "text/markdown": ".md",
}
_SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def _document_extension(path: Path, original_filename: str | None, mime: str | None) -> str:
    if original_filename is not None:
        original_extension = Path(original_filename).suffix.lower()
        if original_extension in _SUPPORTED_EXTENSIONS:
            extension = original_extension
        else:
            raise DocumentParseError("Unsupported document type; expected PDF, DOCX, TXT, or MD")
    else:
        extension = path.suffix.lower()
        if extension not in _SUPPORTED_EXTENSIONS:
            if extension or not mime:
                raise DocumentParseError("Unsupported document type; expected PDF, DOCX, TXT, or MD")
            extension = _MIME_EXTENSIONS.get(mime.partition(";")[0].strip().lower(), "")

    if extension not in _SUPPORTED_EXTENSIONS:
        raise DocumentParseError("Unsupported document type; expected PDF, DOCX, TXT, or MD")
    if mime:
        mime_extension = _MIME_EXTENSIONS.get(mime.partition(";")[0].strip().lower())
        if mime_extension != extension:
            raise DocumentParseError("MIME type does not match the declared document type")
    return extension


def _make_segments(items: list[tuple[str, int]], source_type: str, position: str) -> list[TextSegment]:
    segments: list[TextSegment] = []
    document_offset = 0
    for text, number in items:
        if not text.strip():
            continue
        end = document_offset + len(text)
        segments.append(
            TextSegment(
                text=text,
                source_type=source_type,
                char_start=document_offset,
                char_end=end,
                page=number if position == "page" else None,
                paragraph=number if position == "paragraph" else None,
            )
        )
        document_offset = end
    return segments


def _parse_text(stream: BufferedReader, source_type: str) -> list[TextSegment]:
    try:
        contents = stream.read()
        signature_probe = contents.removeprefix(b"\xef\xbb\xbf")
        if b"\x00" in contents or signature_probe.startswith(
            (b"%PDF-", b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
        ):
            raise DocumentParseError(f"{source_type.upper()} content does not match its declared type")
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DocumentParseError(f"{source_type.upper()} document must be valid UTF-8") from exc
    return _make_segments([(text, 1)], source_type, "none")


def _validate_docx_package(stream: BufferedReader) -> None:
    if stream.read(4) != b"PK\x03\x04":
        raise DocumentParseError("DOCX content does not match its declared type")
    stream.seek(0)
    if not zipfile.is_zipfile(stream):
        raise DocumentParseError("DOCX content does not match its declared type")
    stream.seek(0)
    try:
        with zipfile.ZipFile(stream) as archive:
            members = archive.infolist()
            names = {member.filename for member in members}
            if {"[Content_Types].xml", "word/document.xml"} - names:
                raise DocumentParseError("DOCX package is missing required package members")
            if len(members) > MAX_DOCX_MEMBERS:
                raise DocumentParseError("DOCX package exceeds the member limit")
            total_size = 0
            for member in members:
                if member.file_size > MAX_DOCX_MEMBER_BYTES:
                    raise DocumentParseError("DOCX package exceeds the member size limit")
                total_size += member.file_size
                if total_size > MAX_DOCX_UNCOMPRESSED_BYTES:
                    raise DocumentParseError("DOCX package exceeds the uncompressed size limit")
                if member.file_size and member.file_size / max(member.compress_size, 1) > MAX_DOCX_COMPRESSION_RATIO:
                    raise DocumentParseError("DOCX package exceeds the compression ratio limit")
    except DocumentParseError:
        raise
    except (OSError, zipfile.BadZipFile) as exc:
        raise DocumentParseError("Could not parse DOCX package") from exc
    finally:
        stream.seek(0)


def _parse_docx(stream: BufferedReader) -> list[TextSegment]:
    _validate_docx_package(stream)
    try:
        document = Document(stream)
        items = [(paragraph.text, number) for number, paragraph in enumerate(document.paragraphs, start=1)]
    except Exception as exc:
        raise DocumentParseError("Could not parse DOCX document") from exc
    return _make_segments(items, "docx", "paragraph")


def _parse_pdf(stream: BufferedReader) -> list[TextSegment]:
    if stream.read(5) != b"%PDF-":
        raise DocumentParseError("PDF content does not match its declared type")
    stream.seek(0)
    try:
        reader = PdfReader(stream)
        if reader.is_encrypted:
            raise DocumentParseError("Encrypted PDF documents are not supported")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise DocumentParseError("PDF document exceeds the page limit")
        items: list[tuple[str, int]] = []
        extracted_chars = 0
        for number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            extracted_chars += len(text)
            if extracted_chars > MAX_PDF_EXTRACTED_CHARS:
                raise DocumentParseError("PDF document exceeds the extracted text limit")
            items.append((text, number))
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError("Could not parse PDF document") from exc
    return _make_segments(items, "pdf", "page")


def parse_document(
    path: str | Path,
    original_filename: str | None = None,
    mime: str | None = None,
) -> list[TextSegment]:
    """Parse one supported document without loading macros or external resources."""
    document_path = Path(path)
    extension = _document_extension(document_path, original_filename, mime)
    try:
        if document_path.stat().st_size > MAX_FILE_BYTES:
            raise DocumentParseError("Document exceeds the file size limit")
        with document_path.open("rb") as stream:
            if extension in {".txt", ".md"}:
                segments = _parse_text(stream, extension[1:])
            elif extension == ".docx":
                segments = _parse_docx(stream)
            else:
                segments = _parse_pdf(stream)
    except DocumentParseError:
        raise
    except OSError as exc:
        raise DocumentParseError("Could not access document") from exc

    if not segments:
        if extension == ".pdf":
            raise DocumentParseError("PDF document contains no extractable text")
        raise DocumentParseError(f"{extension[1:].upper()} document is empty")
    return segments
