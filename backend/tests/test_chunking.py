import pytest

from app.knowledge_base.chunking import TextChunk, chunk_segments
from app.knowledge_base import chunking
from app.knowledge_base.loaders import TextSegment


def segment(text: str, *, start: int = 0, page: int | None = None, paragraph: int | None = None) -> TextSegment:
    return TextSegment(
        text=text,
        source_type="pdf" if page else "docx" if paragraph else "txt",
        page=page,
        paragraph=paragraph,
        char_start=start,
        char_end=start + len(text),
    )


def test_segment_metadata_has_the_documented_positional_order() -> None:
    item = TextSegment("text", "pdf", 3, None, 10, 14)

    assert (item.page, item.paragraph, item.char_start, item.char_end) == (3, None, 10, 14)


def test_default_chunk_size_and_overlap_cover_950_characters() -> None:
    chunks = chunk_segments([segment("中" * 950)])

    assert [len(chunk.text) for chunk in chunks] == [500, 500]
    assert [(chunk.segment_char_start, chunk.segment_char_end) for chunk in chunks] == [(0, 500), (450, 950)]
    assert [(chunk.char_start, chunk.char_end) for chunk in chunks] == [(0, 500), (450, 950)]
    assert "".join([chunks[0].text[:450], chunks[1].text]) == "中" * 950


def test_short_and_boundary_length_text_each_make_one_chunk() -> None:
    chunks = chunk_segments([segment("a" * 12), segment("b" * 500, start=12)])

    assert [len(chunk.text) for chunk in chunks] == [12, 500]
    assert all(isinstance(chunk, TextChunk) for chunk in chunks)


def test_chunks_do_not_cross_segments_and_keep_source_metadata() -> None:
    segments = [segment("a" * 6, start=10, page=2), segment("b" * 7, start=16, paragraph=4), segment(" \n", start=23)]

    chunks = chunk_segments(segments, chunk_size=5, overlap=2)

    assert [chunk.text for chunk in chunks] == ["a" * 5, "a" * 3, "b" * 5, "b" * 4]
    assert [(chunk.page, chunk.paragraph) for chunk in chunks] == [(2, None), (2, None), (None, 4), (None, 4)]
    assert [(chunk.char_start, chunk.char_end) for chunk in chunks] == [(10, 15), (13, 16), (16, 21), (19, 23)]
    assert [(chunk.segment_char_start, chunk.segment_char_end) for chunk in chunks] == [(0, 5), (3, 6), (0, 5), (3, 7)]


@pytest.mark.parametrize(("chunk_size", "overlap"), [(0, 0), (-1, 0), (10, -1), (10, 10), (10, 11)])
def test_invalid_chunk_parameters_raise_value_error(chunk_size: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        chunk_segments([segment("text")], chunk_size=chunk_size, overlap=overlap)


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [
        (True, 0),
        (False, 0),
        (10.5, 0),
        ("10", 0),
        (None, 0),
        (10, True),
        (10, False),
        (10, 1.5),
        (10, "1"),
        (10, None),
    ],
)
def test_non_integer_chunk_parameters_raise_value_error(chunk_size: object, overlap: object) -> None:
    with pytest.raises(ValueError, match="integers"):
        chunk_segments([segment("text")], chunk_size=chunk_size, overlap=overlap)  # type: ignore[arg-type]


def test_empty_input_and_whitespace_segments_produce_no_chunks() -> None:
    assert chunk_segments([]) == []
    assert chunk_segments([segment(" \n\t")]) == []


def test_per_segment_chunk_budget_is_checked_before_building(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chunking, "MAX_CHUNKS_PER_SEGMENT", 2)

    with pytest.raises(ValueError, match="per-segment chunk limit"):
        chunk_segments([segment("x" * 20)], chunk_size=5, overlap=4)


def test_total_chunk_budget_is_checked_before_building(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chunking, "MAX_TOTAL_CHUNKS", 3)

    with pytest.raises(ValueError, match="total chunk limit"):
        chunk_segments([segment("a" * 6), segment("b" * 6, start=6)], chunk_size=5, overlap=2)
