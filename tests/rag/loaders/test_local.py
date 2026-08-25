import pytest

from src.rag.loaders.local import LocalLoader
from src.rag.loaders.models import LoadError


def test_nonexistent_directory_raises_load_error(tmp_path):
    with pytest.raises(LoadError):
        list(LocalLoader(tmp_path / "does-not-exist").load())


def test_walks_nested_files_with_posix_relative_paths(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.py").write_bytes(b"top level")
    (tmp_path / "sub" / "b.py").write_bytes(b"nested")

    files = {f.path: f.data for f in LocalLoader(tmp_path).load()}
    assert files == {"a.py": b"top level", "sub/b.py": b"nested"}


def test_git_directory_is_excluded(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_bytes(b"ref: refs/heads/main")
    (tmp_path / "a.py").write_bytes(b"x")

    files = [f.path for f in LocalLoader(tmp_path).load()]
    assert files == ["a.py"]
