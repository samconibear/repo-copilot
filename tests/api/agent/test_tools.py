import pytest

from src.api.agent.tools import TOOL_SCHEMAS, dispatch


def test_tool_schemas_names_match_dispatch_branches():
    names = {s["name"] for s in TOOL_SCHEMAS}
    assert names == {"search_code", "read_file", "list_files"}


def test_dispatch_search_code_passes_query_and_default_top_k(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "src.api.agent.tools.impl.search_code",
        lambda repo, query, top_k: captured.update(repo=repo, query=query, top_k=top_k),
    )
    dispatch("repo", "search_code", {"query": "how does auth work"})
    assert captured == {"repo": "repo", "query": "how does auth work", "top_k": 10}


def test_dispatch_read_file_passes_path(monkeypatch):
    monkeypatch.setattr("src.api.agent.tools.impl.read_file", lambda repo, path: f"{repo}:{path}")
    assert dispatch("repo", "read_file", {"path": "a.py"}) == "repo:a.py"


def test_dispatch_list_files_ignores_input(monkeypatch):
    monkeypatch.setattr("src.api.agent.tools.impl.list_files", lambda repo: ["a.py"])
    assert dispatch("repo", "list_files", {}) == ["a.py"]


def test_dispatch_unknown_tool_raises_value_error():
    with pytest.raises(ValueError, match="unknown tool"):
        dispatch("repo", "delete_everything", {})
