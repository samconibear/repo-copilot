"""Chunk = chunk_symbols()/chunk_text() output. ChunkConfig = size-
threshold schema, instances in registry.py. Mirrors parsing/models.py's
split: types here, the registry of actual instances there.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkConfig:
    """Size thresholds driving every chunking decision - see
    plans/04-chunking.md decision #7. All char-based, not token-based
    (no tokenizer dependency at this layer). Model-dependent in
    principle (decision #8) - this type is the shape that gets tuned
    per embedding model, registry.py holds the actual instances."""

    split_threshold: int  # chars - content beyond this gets windowed
    window_size: int  # chars per window
    window_overlap: int  # chars carried into next window's start
    gap_min_size: int  # chars of non-whitespace - floor for a gap to become a chunk


@dataclass(frozen=True)
class Chunk:
    """key: "file_path::label@start_line", +"#N" if split (N = 1-indexed
    window). label is qualified_name for symbol chunks, "<gap>"/"<text>"
    placeholder for the other two - one key format, not three.
    start_line is the whole symbol/gap's start, not the window's own -
    split chunks share their parent's key base by design (plans/04-chunking.md #6).
    """

    key: str
    file_path: str
    content: str  # raw text, verbatim - never synthetic (plans/04-chunking.md #5)
    chunk_type: str  # "symbol" | "gap" | "text"
    start_line: int
    end_line: int
    qualified_name: str | None  # None for gap/text
    symbol_kind: str | None  # Symbol.kind; None for gap/text
    parent: str | None  # Symbol.parent; None for gap/text
    part: int | None  # 1-indexed split index, None if not split
    part_count: int | None  # total parts if split, None if not split
