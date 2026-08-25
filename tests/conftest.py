import pytest

from src.rag.chunking.models import Chunk
from src.rag.embedding.models import Embedding


def make_chunk(
    key: str = "a.py::foo@1",
    file_path: str = "a.py",
    content: str = "def foo():\n    pass\n",
    chunk_type: str = "symbol",
    start_line: int = 1,
    end_line: int = 2,
    qualified_name: str | None = "foo",
    symbol_kind: str | None = "function",
    parent: str | None = None,
    part: int | None = None,
    part_count: int | None = None,
) -> Chunk:
    return Chunk(
        key=key,
        file_path=file_path,
        content=content,
        chunk_type=chunk_type,
        start_line=start_line,
        end_line=end_line,
        qualified_name=qualified_name,
        symbol_kind=symbol_kind,
        parent=parent,
        part=part,
        part_count=part_count,
    )


def make_embedding(
    key: str = "a.py::foo@1", file_path: str = "a.py", dim: int = 8, model: str = "test-model"
) -> Embedding:
    return Embedding(key=key, file_path=file_path, vector=[0.1] * dim, model=model, dim=dim)


@pytest.fixture
def chunk_factory():
    return make_chunk


@pytest.fixture
def embedding_factory():
    return make_embedding
