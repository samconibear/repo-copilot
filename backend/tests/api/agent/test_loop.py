import json

from src.api.agent.loop import ask
from src.api.agent.models import AgentConfig

_CONFIG = AgentConfig(max_iterations=3)


def _text_response(text: str, stop_reason: str = "end_turn") -> dict:
    return {"content": [{"type": "text", "text": text}], "stop_reason": stop_reason}


def _tool_use_response(name: str, tool_input: dict, tool_use_id: str = "tu_1") -> dict:
    return {
        "content": [{"type": "tool_use", "id": tool_use_id, "name": name, "input": tool_input}],
        "stop_reason": "tool_use",
    }


def test_immediate_text_answer_returns_extracted_text(monkeypatch):
    monkeypatch.setattr(
        "src.api.agent.loop.client.call",
        lambda messages, system, tools, config: _text_response("the answer"),
    )
    result = ask("repo", "what does this do?", _CONFIG)
    assert result.answer == "the answer"
    assert result.citations == []


def test_tool_use_round_trip_then_final_answer(monkeypatch):
    calls = []

    def fake_call(messages, system, tools, config):
        calls.append([dict(m) for m in messages])
        if len(calls) == 1:
            return _tool_use_response("list_files", {})
        return _text_response("here are the files")

    def fake_dispatch(repo_source, name, tool_input):
        assert repo_source == "repo"
        assert name == "list_files"
        return ["a.py", "b.py"]

    monkeypatch.setattr("src.api.agent.loop.client.call", fake_call)
    monkeypatch.setattr("src.api.agent.loop.dispatch", fake_dispatch)

    result = ask("repo", "what files exist?", _CONFIG)

    assert result.answer == "here are the files"
    assert len(calls) == 2
    second_call_messages = calls[1]
    assert second_call_messages[1]["role"] == "assistant"
    tool_result_message = second_call_messages[2]
    assert tool_result_message["role"] == "user"
    [tool_result] = tool_result_message["content"]
    assert tool_result["type"] == "tool_result"
    assert tool_result["tool_use_id"] == "tu_1"
    assert json.loads(tool_result["content"]) == ["a.py", "b.py"]


def test_dispatch_error_is_reported_back_as_a_tool_result_not_raised(monkeypatch):
    calls = []

    def fake_call(messages, system, tools, config):
        calls.append(messages)
        if len(calls) == 1:
            return _tool_use_response("read_file", {"path": "missing.py"})
        return _text_response("couldn't find it")

    def fake_dispatch(repo_source, name, tool_input):
        raise ValueError("no such file")

    monkeypatch.setattr("src.api.agent.loop.client.call", fake_call)
    monkeypatch.setattr("src.api.agent.loop.dispatch", fake_dispatch)

    result = ask("repo", "read missing.py", _CONFIG)

    assert result.answer == "couldn't find it"
    [tool_result] = calls[1][2]["content"]
    assert json.loads(tool_result["content"]) == {"error": "no such file"}


def test_exhausting_max_iterations_returns_fallback_message(monkeypatch):
    config = AgentConfig(max_iterations=2)
    monkeypatch.setattr(
        "src.api.agent.loop.client.call",
        lambda messages, system, tools, config: _tool_use_response("list_files", {}),
    )
    monkeypatch.setattr("src.api.agent.loop.dispatch", lambda repo, name, inp: [])

    result = ask("repo", "q", config)
    assert result.answer == "(reached max tool-call iterations without a final answer)"


class TestCitations:
    def test_search_code_results_are_accumulated_as_citations(self, monkeypatch):
        calls = []
        search_hits = [{"file_path": "a.py", "content": "x", "score": 0.9}]

        def fake_call(messages, system, tools, config):
            calls.append(None)
            if len(calls) == 1:
                return _tool_use_response("search_code", {"query": "q"})
            return _text_response("done")

        monkeypatch.setattr("src.api.agent.loop.client.call", fake_call)
        monkeypatch.setattr("src.api.agent.loop.dispatch", lambda repo, name, inp: search_hits)

        result = ask("repo", "q", _CONFIG)
        assert result.citations == search_hits

    def test_read_file_results_are_captured_as_a_whole_file_citation(self, monkeypatch):
        calls = []

        def fake_call(messages, system, tools, config):
            calls.append(None)
            if len(calls) == 1:
                return _tool_use_response("read_file", {"path": "a.py"})
            return _text_response("done")

        monkeypatch.setattr("src.api.agent.loop.client.call", fake_call)
        monkeypatch.setattr(
            "src.api.agent.loop.dispatch", lambda repo, name, inp: "line one\nline two\nline three"
        )

        result = ask("repo", "q", _CONFIG)
        assert result.citations == [
            {
                "file_path": "a.py",
                "content": "line one\nline two\nline three",
                "chunk_type": "file",
                "start_line": 1,
                "end_line": 3,
                "qualified_name": None,
                "symbol_kind": None,
                "parent": None,
                "score": "Bypassed RAG - read full file",
            }
        ]

    def test_list_files_results_are_not_captured_as_citations(self, monkeypatch):
        calls = []

        def fake_call(messages, system, tools, config):
            calls.append(None)
            if len(calls) == 1:
                return _tool_use_response("list_files", {})
            return _text_response("done")

        monkeypatch.setattr("src.api.agent.loop.client.call", fake_call)
        monkeypatch.setattr("src.api.agent.loop.dispatch", lambda repo, name, inp: ["a.py", "b.py"])

        result = ask("repo", "q", _CONFIG)
        assert result.citations == []

    def test_duplicate_chunk_within_one_search_code_call_is_not_repeated(self, monkeypatch):
        calls = []
        dup_hit = {"file_path": "a.py", "start_line": 1, "end_line": 5, "content": "x", "score": 0.9}
        search_hits = [dup_hit, dict(dup_hit)]

        def fake_call(messages, system, tools, config):
            calls.append(None)
            if len(calls) == 1:
                return _tool_use_response("search_code", {"query": "q"})
            return _text_response("done")

        monkeypatch.setattr("src.api.agent.loop.client.call", fake_call)
        monkeypatch.setattr("src.api.agent.loop.dispatch", lambda repo, name, inp: search_hits)

        result = ask("repo", "q", _CONFIG)
        assert result.citations == [dup_hit]

    def test_same_chunk_across_two_search_code_calls_is_not_repeated(self, monkeypatch):
        calls = []
        hit = {"file_path": "a.py", "start_line": 1, "end_line": 5, "content": "x", "score": 0.9}

        def fake_call(messages, system, tools, config):
            calls.append(None)
            if len(calls) <= 2:
                return _tool_use_response("search_code", {"query": f"q{len(calls)}"})
            return _text_response("done")

        monkeypatch.setattr("src.api.agent.loop.client.call", fake_call)
        monkeypatch.setattr("src.api.agent.loop.dispatch", lambda repo, name, inp: [dict(hit)])

        result = ask("repo", "q", _CONFIG)
        assert result.citations == [hit]

    def test_read_file_citation_matching_an_existing_search_code_range_is_not_repeated(
        self, monkeypatch
    ):
        calls = []
        search_hit = {
            "file_path": "a.py",
            "start_line": 1,
            "end_line": 3,
            "content": "line one\nline two\nline three",
            "score": 0.9,
        }

        def fake_call(messages, system, tools, config):
            calls.append(None)
            if len(calls) == 1:
                return _tool_use_response("search_code", {"query": "q"})
            if len(calls) == 2:
                return _tool_use_response("read_file", {"path": "a.py"})
            return _text_response("done")

        def fake_dispatch(repo, name, inp):
            if name == "search_code":
                return [dict(search_hit)]
            return "line one\nline two\nline three"

        monkeypatch.setattr("src.api.agent.loop.client.call", fake_call)
        monkeypatch.setattr("src.api.agent.loop.dispatch", fake_dispatch)

        result = ask("repo", "q", _CONFIG)
        # Same file_path/start_line/end_line as the search_code hit - the
        # read_file citation is dropped, first occurrence wins.
        assert result.citations == [search_hit]

    def test_read_file_error_is_not_captured_as_a_citation(self, monkeypatch):
        calls = []

        def fake_call(messages, system, tools, config):
            calls.append(None)
            if len(calls) == 1:
                return _tool_use_response("read_file", {"path": "missing.py"})
            return _text_response("done")

        monkeypatch.setattr("src.api.agent.loop.client.call", fake_call)

        def fake_dispatch(repo, name, inp):
            raise ValueError("no such file")

        monkeypatch.setattr("src.api.agent.loop.dispatch", fake_dispatch)

        result = ask("repo", "q", _CONFIG)
        assert result.citations == []
