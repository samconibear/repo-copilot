from src.api.mcp import tools
from src.rag.storage.models import SearchResult
from tests.conftest import make_chunk


def test_search_code_embeds_query_then_searches_and_flattens_results(monkeypatch):
    captured = {}

    def fake_embed_query(query):
        captured["query"] = query
        return [0.1]

    monkeypatch.setattr("src.api.mcp.tools.embed_query", fake_embed_query)

    def fake_search(repo_source, vector, top_k):
        captured["search_args"] = (repo_source, vector, top_k)
        chunk = make_chunk(qualified_name="foo", symbol_kind="function")
        return [SearchResult(chunk=chunk, score=0.9)]

    monkeypatch.setattr("src.api.mcp.tools.storage.search", fake_search)

    result = tools.search_code("some-repo", "how does foo work", top_k=5)

    assert captured["query"] == "how does foo work"
    assert captured["search_args"] == ("some-repo", [0.1], 5)
    assert result == [
        {
            "file_path": "a.py",
            "content": "def foo():\n    pass\n",
            "chunk_type": "symbol",
            "start_line": 1,
            "end_line": 2,
            "qualified_name": "foo",
            "symbol_kind": "function",
            "parent": None,
            "score": 0.9,
        }
    ]


def test_read_file_delegates_to_storage(monkeypatch):
    monkeypatch.setattr(
        "src.api.mcp.tools.storage.read_file",
        lambda repo_source, path: f"contents of {path} in {repo_source}",
    )
    assert tools.read_file("repo", "a.py") == "contents of a.py in repo"


def test_list_files_delegates_to_storage(monkeypatch):
    monkeypatch.setattr("src.api.mcp.tools.storage.list_files", lambda repo_source: ["a.py", "b.py"])
    assert tools.list_files("repo") == ["a.py", "b.py"]
