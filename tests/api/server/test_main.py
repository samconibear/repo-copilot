import json

import pytest
from fastapi.testclient import TestClient

from src.api.server.main import app
from src.rag.loaders.models import LoadError
from src.rag.storage.models import RepoInfo
from src.api.agent.models import AgentError, AgentResult


@pytest.fixture
def client():
    return TestClient(app)


def _events(response) -> list[dict]:
    return [json.loads(line) for line in response.text.splitlines() if line]


class TestIngestEndpoint:
    def test_successful_ingest_streams_progress_then_a_done_event(self, client, monkeypatch):
        def fake_stream(repo_source):
            assert repo_source == "https://github.com/o/r"
            yield {"phase": "loading", "files_loaded": 1}
            yield {"phase": "chunking", "chunks_produced": 3}
            yield {"phase": "embedding", "chunks_embedded": 3, "chunks_total": 3}
            yield {"phase": "storing"}
            yield {"phase": "done", "chunks_ingested": 3}

        monkeypatch.setattr("src.api.server.main.ingest_repo_stream", fake_stream)
        response = client.post("/ingest", json={"repo_source": "https://github.com/o/r"})
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/x-ndjson")
        events = _events(response)
        assert events[0]["phase"] == "loading"
        assert events[-1] == {"phase": "done", "chunks_ingested": 3}

    def test_empty_repo_source_is_rejected_before_ingest_runs(self, client, monkeypatch):
        def fail_if_called(repo_source):
            raise AssertionError("ingest_repo_stream should not run for invalid input")

        monkeypatch.setattr("src.api.server.main.ingest_repo_stream", fail_if_called)
        response = client.post("/ingest", json={"repo_source": ""})
        assert response.status_code == 422

    def test_known_ingest_errors_surface_as_a_terminal_error_event(self, client, monkeypatch):
        def raise_error(repo_source):
            yield {"phase": "loading", "files_loaded": 1}
            raise LoadError("something went wrong")

        monkeypatch.setattr("src.api.server.main.ingest_repo_stream", raise_error)
        response = client.post("/ingest", json={"repo_source": "some-repo"})
        assert response.status_code == 200
        events = _events(response)
        assert events[-1] == {"phase": "error", "detail": "something went wrong"}


class TestAskEndpoint:
    def test_successful_ask_returns_answer_and_citations(self, client, monkeypatch):
        captured = {}
        citation = {
            "file_path": "a.py",
            "start_line": 1,
            "end_line": 2,
            "qualified_name": "foo",
            "score": 0.9,
            "content": "def foo(): pass",
        }

        def fake_ask(repo_source, question):
            captured["args"] = (repo_source, question)
            return AgentResult(answer="42", citations=[citation])

        monkeypatch.setattr("src.api.server.main.agent_ask", fake_ask)
        response = client.post(
            "/ask", json={"repo_source": "some-repo", "question": "what is the answer?"}
        )
        assert response.status_code == 200
        assert response.json() == {
            "repo_source": "some-repo",
            "answer": "42",
            "citations": [citation],
        }
        assert captured["args"] == ("some-repo", "what is the answer?")

    def test_citation_extra_fields_from_search_results_are_dropped(self, client, monkeypatch):
        raw_hit = {
            "file_path": "a.py",
            "content": "x",
            "chunk_type": "symbol",
            "start_line": 1,
            "end_line": 2,
            "qualified_name": "foo",
            "symbol_kind": "function",
            "parent": None,
            "score": 0.9,
        }
        monkeypatch.setattr(
            "src.api.server.main.agent_ask",
            lambda repo_source, question: AgentResult(answer="ok", citations=[raw_hit]),
        )
        response = client.post("/ask", json={"repo_source": "some-repo", "question": "q"})
        [citation] = response.json()["citations"]
        assert set(citation.keys()) == {
            "file_path",
            "start_line",
            "end_line",
            "qualified_name",
            "score",
            "content",
        }

    def test_empty_question_is_rejected(self, client, monkeypatch):
        def fail_if_called(repo_source, question):
            raise AssertionError("agent_ask should not run for invalid input")

        monkeypatch.setattr("src.api.server.main.agent_ask", fail_if_called)
        response = client.post("/ask", json={"repo_source": "some-repo", "question": ""})
        assert response.status_code == 422

    def test_agent_error_maps_to_502(self, client, monkeypatch):
        def raise_agent_error(repo_source, question):
            raise AgentError("Anthropic API error 500: boom")

        monkeypatch.setattr("src.api.server.main.agent_ask", raise_agent_error)
        response = client.post("/ask", json={"repo_source": "some-repo", "question": "q"})
        assert response.status_code == 502
        assert response.json()["detail"] == "Anthropic API error 500: boom"


class TestReposEndpoint:
    def test_returns_repos_sorted_most_recently_ingested_first(self, client, monkeypatch):
        older = RepoInfo(repo_source="a", chunks_ingested=1, ingested_at="2026-01-01T00:00:00+00:00")
        newer = RepoInfo(repo_source="b", chunks_ingested=2, ingested_at="2026-06-01T00:00:00+00:00")
        monkeypatch.setattr("src.api.server.main.list_repos", lambda: [older, newer])

        response = client.get("/repos")
        assert response.status_code == 200
        assert [r["repo_source"] for r in response.json()] == ["b", "a"]
