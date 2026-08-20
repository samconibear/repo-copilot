from ..embedding.engine import embed_query
from ..storage import engine as storage
from ..storage.models import SearchResult


def search_code(repo_source: str, query: str, top_k: int = 10) -> list[dict]:
    vector = embed_query(query)
    results = storage.search(repo_source, vector, top_k)
    return [_result_to_dict(r) for r in results]


def read_file(repo_source: str, path: str) -> str:
    return storage.read_file(repo_source, path)


def list_files(repo_source: str) -> list[str]:
    return storage.list_files(repo_source)


def _result_to_dict(result: SearchResult) -> dict:
    chunk = result.chunk
    return {
        "file_path": chunk.file_path,
        "content": chunk.content,
        "chunk_type": chunk.chunk_type,
        "start_line": chunk.start_line,
        "end_line": chunk.end_line,
        "qualified_name": chunk.qualified_name,
        "symbol_kind": chunk.symbol_kind,
        "parent": chunk.parent,
        "score": result.score,
    }
