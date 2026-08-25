import io
import tarfile
import urllib.error

import pytest

from src.rag.loaders.git import GitLoader
from src.rag.loaders.models import LoadError


def _make_tarball(entries: dict[str, bytes], top_dir: str = "owner-repo-abc123") -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for rel_path, data in entries.items():
            info = tarfile.TarInfo(name=f"{top_dir}/{rel_path}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


class TestUrlValidation:
    @pytest.mark.parametrize("url", ["not-a-url", "https://gitlab.com/owner/repo"])
    def test_invalid_urls_raise_load_error(self, url):
        with pytest.raises(LoadError):
            GitLoader(url)

    def test_valid_url_is_accepted(self):
        GitLoader("https://github.com/owner/repo")


class TestLoad:
    def test_strips_top_level_dir_and_excludes_git(self, monkeypatch):
        tarball = _make_tarball(
            {"a.py": b"hello", "sub/b.py": b"world", ".git/config": b"[core]"}
        )
        monkeypatch.setattr(
            "src.rag.loaders.git.urllib.request.urlopen",
            lambda *a, **k: io.BytesIO(tarball),
        )

        files = {f.path: f.data for f in GitLoader("https://github.com/owner/repo").load()}
        assert files == {"a.py": b"hello", "sub/b.py": b"world"}

    def test_http_error_raises_load_error(self, monkeypatch):
        def raise_http_error(*a, **k):
            raise urllib.error.HTTPError("url", 404, "Not Found", {}, None)

        monkeypatch.setattr("src.rag.loaders.git.urllib.request.urlopen", raise_http_error)
        with pytest.raises(LoadError, match="404"):
            list(GitLoader("https://github.com/owner/repo").load())

    def test_url_error_raises_load_error(self, monkeypatch):
        def raise_url_error(*a, **k):
            raise urllib.error.URLError("no route to host")

        monkeypatch.setattr("src.rag.loaders.git.urllib.request.urlopen", raise_url_error)
        with pytest.raises(LoadError, match="no route to host"):
            list(GitLoader("https://github.com/owner/repo").load())
