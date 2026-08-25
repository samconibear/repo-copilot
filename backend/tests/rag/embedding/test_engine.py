import json
import urllib.error

import pytest

from src.rag.embedding.engine import embed_chunks, embed_query, run
from src.rag.embedding.models import EmbedConfig, EmbedError
from tests.conftest import make_chunk

_CONFIG = EmbedConfig(model="test-model", dim=3, batch_size=64, max_batch_chars=200_000)


class _FakeResponse:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _stub_ollama(monkeypatch, vectors_by_call=None, vectors=None, capture: list | None = None):
    calls = iter(vectors_by_call) if vectors_by_call is not None else None

    def fake_urlopen(request, timeout=None):
        if capture is not None:
            capture.append(json.loads(request.data))
        result = next(calls) if calls is not None else vectors
        return _FakeResponse({"embeddings": result})

    monkeypatch.setattr("src.rag.embedding.engine.urllib.request.urlopen", fake_urlopen)


class TestEmbedQuery:
    def test_returns_first_vector_from_ollama_response(self, monkeypatch):
        _stub_ollama(monkeypatch, vectors=[[1.0, 2.0, 3.0]])
        assert embed_query("hello", _CONFIG) == [1.0, 2.0, 3.0]

    def test_http_error_raises_embed_error(self, monkeypatch):
        def raise_http_error(request, timeout=None):
            raise urllib.error.HTTPError("url", 500, "boom", {}, None)

        monkeypatch.setattr("src.rag.embedding.engine.urllib.request.urlopen", raise_http_error)
        with pytest.raises(EmbedError, match="500"):
            embed_query("hello", _CONFIG)

    def test_connection_error_raises_embed_error_with_hint(self, monkeypatch):
        def raise_url_error(request, timeout=None):
            raise urllib.error.URLError("connection refused")

        monkeypatch.setattr("src.rag.embedding.engine.urllib.request.urlopen", raise_url_error)
        with pytest.raises(EmbedError, match="ollama serve"):
            embed_query("hello", _CONFIG)


class TestEmbedChunks:
    def test_each_chunk_gets_its_matching_vector_key_and_model(self, monkeypatch):
        chunks = [make_chunk(key="a::1"), make_chunk(key="a::2")]
        _stub_ollama(monkeypatch, vectors=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        embeddings = embed_chunks(chunks, _CONFIG)
        assert [e.key for e in embeddings] == ["a::1", "a::2"]
        assert all(e.model == "test-model" and e.dim == 3 for e in embeddings)

    def test_header_is_prepended_before_sending_to_ollama(self, monkeypatch):
        chunk = make_chunk(
            chunk_type="symbol",
            file_path="a.py",
            symbol_kind="function",
            qualified_name="foo",
            content="pass",
        )
        captured: list = []
        _stub_ollama(monkeypatch, vectors=[[0.0, 0.0, 0.0]], capture=captured)
        embed_chunks([chunk], _CONFIG)
        assert captured[0]["input"] == ["# a.py :: function foo\npass"]

class TestBatching:
    def test_batch_splits_on_batch_size(self, monkeypatch):
        config = EmbedConfig(model="m", dim=1, batch_size=2, max_batch_chars=1_000_000)
        chunks = [make_chunk(key=f"k{i}", content="x") for i in range(5)]
        calls: list = []
        _stub_ollama(
            monkeypatch,
            vectors_by_call=[[[0.0]] * 2, [[0.0]] * 2, [[0.0]] * 1],
            capture=calls,
        )
        result = list(run(chunks, config))
        assert [len(c["input"]) for c in calls] == [2, 2, 1]
        assert len(result) == 5

    def test_batch_splits_on_max_batch_chars(self, monkeypatch):
        config = EmbedConfig(model="m", dim=1, batch_size=100, max_batch_chars=50)
        chunks = [make_chunk(key=f"k{i}", content="x" * 30) for i in range(2)]
        calls: list = []
        _stub_ollama(monkeypatch, vectors_by_call=[[[0.0]], [[0.0]]], capture=calls)
        result = list(run(chunks, config))
        assert [len(c["input"]) for c in calls] == [1, 1]
        assert len(result) == 2
