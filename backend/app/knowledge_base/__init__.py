"""Document loading and location-aware chunking utilities."""

from .chunking import ChunkingError, TextChunk, chunk_segments
from .loaders import DocumentParseError, TextSegment, parse_document

__all__ = [
    "DocumentParseError",
    "ChunkingError",
    "TextChunk",
    "TextSegment",
    "chunk_segments",
    "parse_document",
]
