import pytest

from src.rag.embedding.models import EmbedError
from src.rag.ingest import ingest_repo, ingest_repo_stream, loader_for
from src.rag.loaders.git import GitLoader
from src.rag.loaders.local import LocalLoader
from src.rag.loaders.models import LoadError


class TestLoaderFor:
    def test_https_url_uses_git_loader(self):
        assert isinstance(loader_for("https://github.com/owner/repo"), GitLoader)

    def test_http_url_is_routed_to_git_loader_but_git_loader_rejects_it(self):
        with pytest.raises(LoadError, match="not a valid GitHub URL"):
            loader_for("http://github.com/owner/repo")

    def test_local_path_uses_local_loader(self):
        assert isinstance(loader_for("./some/path"), LocalLoader)


class _FakeLoader:
    def __init__(self, files):
        self._files = files

    def load(self):
        return iter(self._files)


class TestIngestRepo:
    def test_wires_loader_chunk_embed_and_two_storage_calls(self, monkeypatch):
        from src.rag.loaders.models import SourceFile

        files = [SourceFile(path="a.py", data=b"def f(): pass")]
        chunks_seen = object()
        calls: list[str] = []

        monkeypatch.setattr("src.rag.ingest.loader_for", lambda source: _FakeLoader(files))
        monkeypatch.setattr(
            "src.rag.ingest.chunk_run",
            lambda passed_files, config: (calls.append("chunk"), [chunks_seen])[1],
        )
        monkeypatch.setattr(
            "src.rag.ingest.embed_chunks",
            lambda chunks: (calls.append("embed"), chunks == [chunks_seen], ["fake-embeddings"])[2],
        )

        class _FakeStorage:
            def ingest(self, repo_source, chunks, embeddings):
                calls.append("ingest-chunks")
                assert repo_source == "some-repo"
                assert chunks == [chunks_seen]
                assert embeddings == ["fake-embeddings"]
                return 1

            def ingest_files(self, repo_source, passed_files):
                calls.append("ingest-files")
                assert list(passed_files) == files

        monkeypatch.setattr("src.rag.ingest.storage", _FakeStorage())

        result = ingest_repo("some-repo")

        assert result == 1
        assert calls == ["chunk", "embed", "ingest-chunks", "ingest-files"]

    def test_returns_chunk_count_not_embedding_or_file_count(self, monkeypatch):
        from src.rag.loaders.models import SourceFile

        files = [SourceFile(path="a.py", data=b"x"), SourceFile(path="b.py", data=b"y")]
        monkeypatch.setattr("src.rag.ingest.loader_for", lambda source: _FakeLoader(files))
        monkeypatch.setattr("src.rag.ingest.chunk_run", lambda f, config: [object(), object(), object()])
        monkeypatch.setattr("src.rag.ingest.embed_chunks", lambda chunks: ["e"] * len(chunks))

        class _FakeStorage:
            def ingest(self, repo_source, chunks, embeddings):
                return 999

            def ingest_files(self, repo_source, files):
                pass

        monkeypatch.setattr("src.rag.ingest.storage", _FakeStorage())

        assert ingest_repo("some-repo") == 3


class TestIngestRepoStream:
    def test_yields_one_event_per_phase_in_order_ending_in_done(self, monkeypatch):
        from src.rag.loaders.models import SourceFile

        files = [SourceFile(path="a.py", data=b"def f(): pass")]
        chunk_a, chunk_b = object(), object()
        emb_a, emb_b = object(), object()

        monkeypatch.setattr("src.rag.ingest.loader_for", lambda source: _FakeLoader(files))
        monkeypatch.setattr(
            "src.rag.ingest.chunk_run", lambda passed_files, config: iter([chunk_a, chunk_b])
        )
        monkeypatch.setattr("src.rag.ingest.embed_run", lambda chunks: iter([emb_a, emb_b]))

        storage_calls: list[str] = []

        class _FakeStorage:
            def ingest(self, repo_source, chunks, embeddings):
                storage_calls.append("ingest-chunks")
                assert repo_source == "some-repo"
                assert chunks == [chunk_a, chunk_b]
                assert embeddings == [emb_a, emb_b]

            def ingest_files(self, repo_source, passed_files):
                storage_calls.append("ingest-files")
                assert list(passed_files) == files

        monkeypatch.setattr("src.rag.ingest.storage", _FakeStorage())

        events = list(ingest_repo_stream("some-repo"))

        assert [e["phase"] for e in events] == [
            "loading",
            "loading",
            "chunking",
            "chunking",
            "embedding",
            "embedding",
            "embedding",
            "storing",
            "done",
        ]
        assert events[-1] == {"phase": "done", "chunks_ingested": 2}
        assert storage_calls == ["ingest-chunks", "ingest-files"]

    def test_error_partway_through_propagates_not_swallowed(self, monkeypatch):
        from src.rag.loaders.models import SourceFile

        files = [SourceFile(path="a.py", data=b"x")]
        monkeypatch.setattr("src.rag.ingest.loader_for", lambda source: _FakeLoader(files))
        monkeypatch.setattr("src.rag.ingest.chunk_run", lambda f, config: iter([object()]))

        def failing_embed(chunks):
            raise EmbedError("ollama is down")

        monkeypatch.setattr("src.rag.ingest.embed_run", failing_embed)

        with pytest.raises(EmbedError, match="ollama is down"):
            list(ingest_repo_stream("some-repo"))
