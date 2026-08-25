from src.rag.chunking.engine import chunk_symbols, chunk_text, run
from src.rag.chunking.models import ChunkConfig
from src.rag.chunking.registry import CHUNK_CONFIGS
from src.rag.loaders.models import SourceFile
from src.rag.parsing.models import Symbol

_CONFIG = CHUNK_CONFIGS["default"]


def make_symbol(
    name: str = "foo",
    start_byte: int = 0,
    end_byte: int = 10,
    start_line: int = 1,
    kind: str = "function",
    parent: str | None = None,
    source: str = "def foo():",
) -> Symbol:
    return Symbol(
        file_path="a.py",
        kind=kind,
        name=name,
        qualified_name=f"{parent}.{name}" if parent else name,
        start_line=start_line,
        end_line=start_line,
        start_byte=start_byte,
        end_byte=end_byte,
        signature=source,
        parent=parent,
        source=source,
    )


class TestChunkText:
    def test_short_file_below_gap_min_size_yields_nothing(self):
        assert chunk_text("a.txt", b"hi", _CONFIG) == []

    def test_file_at_or_above_gap_min_size_yields_one_text_chunk(self):
        text = "x" * _CONFIG.gap_min_size
        [chunk] = chunk_text("a.txt", text.encode(), _CONFIG)
        assert chunk.chunk_type == "text"
        assert chunk.content == text
        assert chunk.qualified_name is None
        assert chunk.symbol_kind is None
        assert chunk.key == "a.txt::<text>@1"

class TestChunkSymbols:
    def test_single_symbol_no_surrounding_gap(self):
        source = b"def foo():\n    pass\n"
        sym = make_symbol(start_byte=0, end_byte=len(source))
        chunks = chunk_symbols("a.py", source, [sym], _CONFIG)
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "symbol"
        assert chunks[0].qualified_name == "foo"

    def test_gap_before_and_after_symbol_when_large_enough(self):
        pad = b"#" * 50 + b"\n"
        body = b"def foo():\n    pass\n"
        source = pad + body + pad
        sym = make_symbol(start_byte=len(pad), end_byte=len(pad) + len(body))
        chunks = chunk_symbols("a.py", source, [sym], _CONFIG)
        types = sorted(c.chunk_type for c in chunks)
        assert types == ["gap", "gap", "symbol"]

    def test_small_gap_below_gap_min_size_is_dropped(self):
        source = b"x\n" + b"def foo():\n    pass\n"
        sym = make_symbol(start_byte=2, end_byte=len(source))
        chunks = chunk_symbols("a.py", source, [sym], _CONFIG)
        assert [c.chunk_type for c in chunks] == ["symbol"]

    def test_overlapping_symbols_do_not_double_count_gap_region(self):
        source = b"x" * 100
        a = make_symbol(name="a", start_byte=0, end_byte=60)
        b = make_symbol(name="b", start_byte=30, end_byte=100)
        chunks = chunk_symbols("a.py", source, [a, b], _CONFIG)
        assert [c.chunk_type for c in chunks] == ["symbol", "symbol"]

class TestWindowing:
    def test_content_under_split_threshold_is_a_single_chunk(self):
        config = ChunkConfig(split_threshold=100, window_size=50, window_overlap=10, gap_min_size=1)
        text = "x\n" * 10
        source = text.encode()
        sym = make_symbol(start_byte=0, end_byte=len(source), source=text)
        [chunk] = chunk_symbols("a.py", source, [sym], config)
        assert chunk.part is None
        assert chunk.part_count is None

    def test_content_over_split_threshold_is_split_into_numbered_windows(self):
        config = ChunkConfig(split_threshold=10, window_size=20, window_overlap=5, gap_min_size=1)
        lines = [f"line{i}\n" for i in range(20)]
        source = "".join(lines).encode()
        sym = make_symbol(start_byte=0, end_byte=len(source), source="".join(lines))
        chunks = chunk_symbols("a.py", source, [sym], config)
        assert len(chunks) > 1
        assert [c.part for c in chunks] == list(range(1, len(chunks) + 1))
        assert all(c.part_count == len(chunks) for c in chunks)
        assert all(c.key.endswith(f"#{c.part}") for c in chunks)

class TestRun:
    def test_file_with_no_recognized_language_is_skipped(self, monkeypatch):
        monkeypatch.setattr(
            "src.rag.chunking.engine.language_for_file", lambda f: None
        )
        files = [SourceFile(path="a.bin", data=b"\x00\x01")]
        assert list(run(files, _CONFIG)) == []

    def test_text_language_goes_through_chunk_text_not_parse_file(self, monkeypatch):
        monkeypatch.setattr("src.rag.chunking.engine.language_for_file", lambda f: "text")
        monkeypatch.setattr(
            "src.rag.chunking.engine.parse_file",
            lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not parse text files")),
        )
        files = [SourceFile(path="a.md", data=b"x" * 100)]
        chunks = list(run(files, _CONFIG))
        assert chunks and chunks[0].chunk_type == "text"

    def test_code_language_is_parsed_then_chunked_as_symbols(self, monkeypatch):
        sym = make_symbol(start_byte=0, end_byte=5)
        monkeypatch.setattr("src.rag.chunking.engine.language_for_file", lambda f: "python")
        monkeypatch.setattr(
            "src.rag.chunking.engine.parse_file", lambda path, lang, data: [sym]
        )
        files = [SourceFile(path="a.py", data=b"12345")]
        chunks = list(run(files, _CONFIG))
        assert [c.chunk_type for c in chunks] == ["symbol"]
