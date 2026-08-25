from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkConfig:
    split_threshold: int  # chars content beyond this gets windowed
    window_size: int  # chars per window
    window_overlap: int  # chars carried into next window's start
    gap_min_size: int  # chars floor for a gap to become a chunk


@dataclass(frozen=True)
class Chunk:
    key: str
    file_path: str
    content: str
    chunk_type: str  # "symbol" | "gap" | "text"
    start_line: int
    end_line: int
    qualified_name: str | None  # None for gap/text
    symbol_kind: str | None # None for gap/text
    parent: str | None  # None for gap/text
    part: int | None
    part_count: int | None
