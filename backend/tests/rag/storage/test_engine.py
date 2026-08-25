import pytest

from src.rag.embedding.models import Embedding
from src.rag.storage import engine as storage
from src.rag.storage.models import StoreError
from tests.conftest import make_chunk, make_embedding

_DIM = 768


def _vec(hot_index: int, dim: int = _DIM) -> list[float]:
    v = [0.0] * dim
    v[hot_index] = 1.0
    return v


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DEFAULT_ROOT", tmp_path)
    real_db_path = storage._db_path
    real_list_repos = storage.list_repos
    monkeypatch.setattr(storage, "_db_path", lambda repo_source, root=tmp_path: real_db_path(repo_source, root))
    monkeypatch.setattr(storage, "list_repos", lambda root=tmp_path: real_list_repos(root))


class TestIngestValidation:
    def test_chunk_embedding_length_mismatch_raises(self):
        chunks = [make_chunk(key="a")]
        embeddings = [make_embedding(key="a", dim=_DIM), make_embedding(key="b", dim=_DIM)]
        with pytest.raises(StoreError, match="length mismatch"):
            storage.ingest("repo", chunks, embeddings)

    def test_key_mismatch_between_chunk_and_embedding_raises(self):
        chunks = [make_chunk(key="a")]
        embeddings = [make_embedding(key="different", dim=_DIM)]
        with pytest.raises(StoreError, match="key mismatch"):
            storage.ingest("repo", chunks, embeddings)

    def test_embedding_dim_mismatch_raises(self):
        chunks = [make_chunk(key="a")]
        embeddings = [make_embedding(key="a", dim=8)]
        with pytest.raises(StoreError, match="dim"):
            storage.ingest("repo", chunks, embeddings)


class TestIngestAndSearchRoundTrip:
    def test_ingest_returns_chunk_count(self):
        chunks = [make_chunk(key="a"), make_chunk(key="b")]
        embeddings = [make_embedding(key="a", dim=_DIM), make_embedding(key="b", dim=_DIM)]
        assert storage.ingest("repo", chunks, embeddings) == 2

    def test_search_ranks_closer_vector_first(self):
        chunks = [make_chunk(key="near"), make_chunk(key="far")]
        embeddings = [
            Embedding(key="near", file_path="a.py", vector=_vec(0), model="m", dim=_DIM),
            Embedding(key="far", file_path="a.py", vector=_vec(1), model="m", dim=_DIM),
        ]
        storage.ingest("repo", chunks, embeddings)

        results = storage.search("repo", _vec(0), top_k=2)
        assert [r.chunk.key for r in results] == ["near", "far"]
        assert results[0].score == pytest.approx(1.0)
        assert results[1].score == pytest.approx(0.0)

    def test_search_before_any_ingest_raises_store_error(self):
        with pytest.raises(StoreError, match="no index"):
            storage.search("never-ingested", _vec(0))

    def test_reingesting_wipes_previous_chunks(self):
        first = [make_chunk(key="old")]
        storage.ingest("repo", first, [make_embedding(key="old", dim=_DIM)])
        second = [make_chunk(key="new")]
        storage.ingest("repo", second, [make_embedding(key="new", dim=_DIM)])

        results = storage.search("repo", _vec(0), top_k=10)
        assert [r.chunk.key for r in results] == ["new"]

    def test_different_repo_sources_are_isolated(self):
        storage.ingest("repo-a", [make_chunk(key="a")], [make_embedding(key="a", dim=_DIM)])
        storage.ingest("repo-b", [make_chunk(key="b")], [make_embedding(key="b", dim=_DIM)])

        assert [r.chunk.key for r in storage.search("repo-a", _vec(0), top_k=10)] == ["a"]
        assert [r.chunk.key for r in storage.search("repo-b", _vec(0), top_k=10)] == ["b"]


class TestFiles:
    def test_read_file_before_ingest_raises_store_error(self):
        with pytest.raises(StoreError, match="no index"):
            storage.read_file("never-ingested", "a.py")

    def test_ingest_files_then_read_and_list(self):
        from src.rag.loaders.models import SourceFile

        files = [SourceFile(path="b.py", data=b"content b"), SourceFile(path="a.py", data=b"content a")]
        storage.ingest("repo", [], [])
        count = storage.ingest_files("repo", files)

        assert count == 2
        assert storage.list_files("repo") == ["a.py", "b.py"]
        assert storage.read_file("repo", "a.py") == "content a"

    def test_read_file_for_unindexed_path_raises_store_error(self):
        from src.rag.loaders.models import SourceFile

        storage.ingest("repo", [], [])
        storage.ingest_files("repo", [SourceFile(path="a.py", data=b"x")])
        with pytest.raises(StoreError, match="not an indexed file"):
            storage.read_file("repo", "missing.py")


class TestListRepos:
    def test_nonexistent_root_returns_empty_list(self, tmp_path):
        assert storage.list_repos(tmp_path / "does-not-exist") == []

    def test_ingested_repo_appears_with_its_meta_row(self):
        storage.ingest("some-repo", [make_chunk(key="a")], [make_embedding(key="a", dim=_DIM)])

        [info] = storage.list_repos()
        assert info.repo_source == "some-repo"
        assert info.chunks_ingested == 1
        assert info.ingested_at

    def test_reingesting_updates_the_meta_row_not_appends_a_new_one(self):
        storage.ingest("repo", [make_chunk(key="a")], [make_embedding(key="a", dim=_DIM)])
        storage.ingest("repo", [], [])

        [info] = storage.list_repos()
        assert info.chunks_ingested == 0

    def test_db_without_a_meta_table_is_skipped_not_raised(self, tmp_path):
        import apsw

        bogus = tmp_path / "bogus-00000000.db"
        apsw.Connection(str(bogus)).execute("CREATE TABLE unrelated (x TEXT)")

        storage.ingest("repo", [], [])

        repos = storage.list_repos()
        assert [r.repo_source for r in repos] == ["repo"]
