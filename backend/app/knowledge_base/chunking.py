"""Character-based chunking that preserves document and segment positions."""

from dataclasses import dataclass
from typing import Iterable

from .loaders import TextSegment


MAX_CHUNKS_PER_SEGMENT = 10_000
MAX_TOTAL_CHUNKS = 50_000


class ChunkingError(ValueError):
    """Raised when chunking would exceed a configured safety budget."""


@dataclass(frozen=True, slots=True)
class TextChunk:
    text: str
    source_type: str
    page: int | None = None
    paragraph: int | None = None
    char_start: int = 0
    char_end: int = 0
    segment_char_start: int = 0
    segment_char_end: int = 0


def chunk_segments(
    segments: Iterable[TextSegment],
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[TextChunk]:
    """Split each segment independently, using half-open character offsets."""
    if type(chunk_size) is not int or type(overlap) is not int:
        raise ValueError("chunk_size and overlap must be integers")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must satisfy 0 <= overlap < chunk_size")

    step = chunk_size - overlap
    plans: list[tuple[TextSegment, int]] = []
    total_chunks = 0
    for segment in segments:
        if not segment.text.strip():
            continue
        text_length = len(segment.text)
        chunk_count = 1 if text_length <= chunk_size else 1 + (text_length - chunk_size + step - 1) // step
        if chunk_count > MAX_CHUNKS_PER_SEGMENT:
            raise ChunkingError("Input exceeds the per-segment chunk limit")
        total_chunks += chunk_count
        if total_chunks > MAX_TOTAL_CHUNKS:
            raise ChunkingError("Input exceeds the total chunk limit")
        plans.append((segment, chunk_count))

    chunks: list[TextChunk] = []
    for segment, chunk_count in plans:
        local_start = 0
        for _ in range(chunk_count):
            local_end = min(local_start + chunk_size, len(segment.text))
            chunks.append(
                TextChunk(
                    text=segment.text[local_start:local_end],
                    source_type=segment.source_type,
                    char_start=segment.char_start + local_start,
                    char_end=segment.char_start + local_end,
                    segment_char_start=local_start,
                    segment_char_end=local_end,
                    page=segment.page,
                    paragraph=segment.paragraph,
                )
            )
            local_start += step
    return chunks
