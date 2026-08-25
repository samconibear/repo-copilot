from typing import Iterable

from ..filtering import language_for_file
from ..loaders.models import SourceFile
from ..parsing.engine import parse_file
from ..parsing.models import Symbol
from .models import Chunk, ChunkConfig
from .registry import CHUNK_CONFIGS


def chunk_symbols(
    file_path: str,
    source: bytes,
    symbols: list[Symbol],
    config: ChunkConfig = CHUNK_CONFIGS["default"],
) -> list[Chunk]:
    return _chunk(file_path, source, symbols, config)


def chunk_text(
    file_path: str, source: bytes, config: ChunkConfig = CHUNK_CONFIGS["default"]
) -> list[Chunk]:
    """files with non AST grammar"""
    return _chunk(file_path, source, [], config, gap_type="text", gap_label="<text>")


def run(
    files: Iterable[SourceFile], config: ChunkConfig = CHUNK_CONFIGS["default"]
) -> Iterable[Chunk]:
    for file in files:
        language = language_for_file(file)
        if language is None:
            continue
        if language == "text":
            yield from chunk_text(file.path, file.data, config)
            continue
        symbols = parse_file(file.path, language, file.data)
        yield from chunk_symbols(file.path, file.data, symbols, config)


def _chunk(
    file_path: str,
    source: bytes,
    symbols: list[Symbol],
    config: ChunkConfig,
    gap_type: str = "gap",
    gap_label: str = "<gap>",
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for sym in symbols:
        chunks.extend(
            _emit(
                file_path,
                "symbol",
                sym.source,
                sym.start_line,
                config,
                key_label=sym.qualified_name,
                qualified_name=sym.qualified_name,
                symbol_kind=sym.kind,
                parent=sym.parent,
            )
        )

    def gap(start: int, end: int) -> None:
        text = source[start:end].decode("utf-8", errors="replace")
        if len(text.strip()) < config.gap_min_size:
            return
        chunks.extend(
            _emit(
                file_path,
                gap_type,
                text,
                _line_at(source, start),
                config,
                key_label=gap_label,
                qualified_name=None,
                symbol_kind=None,
                parent=None,
            )
        )

    cursor = 0
    for start, end in sorted((s.start_byte, s.end_byte) for s in symbols):
        if start > cursor:
            gap(cursor, start)
        cursor = max(cursor, end)
    if cursor < len(source):
        gap(cursor, len(source))

    return chunks


def _emit(
    file_path: str,
    chunk_type: str,
    text: str,
    start_line: int,
    config: ChunkConfig,
    key_label: str,
    qualified_name: str | None,
    symbol_kind: str | None,
    parent: str | None,
) -> list[Chunk]:
    windows = _windows(text, start_line, config)
    part_count = len(windows) if len(windows) > 1 else None
    chunks = []
    for idx, (wtext, wstart, wend) in enumerate(windows, start=1):
        key = f"{file_path}::{key_label}@{start_line}"
        if part_count:
            key += f"#{idx}"
        chunks.append(
            Chunk(
                key=key,
                file_path=file_path,
                content=wtext,
                chunk_type=chunk_type,
                start_line=wstart,
                end_line=wend,
                qualified_name=qualified_name,
                symbol_kind=symbol_kind,
                parent=parent,
                part=idx if part_count else None,
                part_count=part_count,
            )
        )
    return chunks


def _windows(text: str, start_line: int, config: ChunkConfig) -> list[tuple[str, int, int]]:
    if len(text) <= config.split_threshold:
        return [(text, start_line, start_line + text.count("\n"))]

    lines = text.splitlines(keepends=True)
    n = len(lines)
    out: list[tuple[str, int, int]] = []
    i = 0
    while i < n:
        j = i
        size = 0
        while j < n and (size == 0 or size + len(lines[j]) <= config.window_size):
            size += len(lines[j])
            j += 1
        out.append(("".join(lines[i:j]), start_line + i, start_line + j - 1))
        if j >= n:
            break
        k = j
        back = 0
        while k > i + 1 and back < config.window_overlap:
            k -= 1
            back += len(lines[k])
        i = k
    return out


def _line_at(source: bytes, byte_offset: int) -> int:
    return source.count(b"\n", 0, byte_offset) + 1
