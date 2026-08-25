import re
import ssl
import tarfile
import urllib.error
import urllib.request
from typing import Iterable

import certifi

from .models import LoadError, SourceFile

_GITHUB_HTTPS_RE = re.compile(
    r"^https://github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(\.git)?/?$"
)

_TARBALL_URL = "https://codeload.github.com/{owner}/{repo}/tar.gz/HEAD"

# Explicit CA bundle rather than relying on the interpreter's default SSL
# context: pyenv-built (and many Linux) Pythons aren't linked into the
# OS's trust store, so urlopen() fails CERTIFICATE_VERIFY_FAILED without
# this — not specific to any one machine's setup.
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


class GitLoader:
    """
    Implements Loader
    Streams a GitHub repo's tarball straight into memory and yields its
    file contents directly — no clone, no scratch directory, no disk
    writes, no `git` binary dependency.

    Trade-offs versus an actual `git clone`:
    - Public repos only (no ambient SSH/git-credential reuse).
    - No incremental refresh — every load() re-downloads the full
      tarball from scratch.
    - Always the repo's default branch (HEAD) — no ref/branch selection.
    """
    def __init__(self, url: str):
        match = _GITHUB_HTTPS_RE.match(url)
        if not match:
            raise LoadError(
                f"'{url}' is not a valid GitHub URL (https://github.com/owner/repo)"
            )
        self._owner = match["owner"]
        self._repo = match["repo"]

    def load(self) -> Iterable[SourceFile]:
        url = _TARBALL_URL.format(owner=self._owner, repo=self._repo)
        try:
            response = urllib.request.urlopen(url, timeout=120, context=_SSL_CONTEXT)
        except urllib.error.HTTPError as e:
            raise LoadError(f"failed to download {url}: HTTP {e.code}") from None
        except urllib.error.URLError as e:
            raise LoadError(f"failed to download {url}: {e.reason}") from None

        try:
            # "r|gz" = stream mode: reads the gzip stream forward-only as
            # it arrives, no seeking, no full-tarball buffering. Each
            # member's bytes are only materialized when we .read() it.
            with response, tarfile.open(fileobj=response, mode="r|gz") as tar:
                for member in tar:
                    if not member.isfile():
                        continue
                    # GitHub tarballs wrap everything in a top-level
                    # "<owner>-<repo>-<sha>/" directory — strip it so
                    # paths match what a plain clone would give you.
                    rel = member.name.split("/", 1)[1] if "/" in member.name else ""
                    if not rel or rel.split("/", 1)[0] == ".git":
                        continue
                    extracted = tar.extractfile(member)
                    if extracted is None:
                        continue
                    yield SourceFile(path=rel, data=extracted.read())
        except (tarfile.TarError, OSError) as e:
            raise LoadError(f"failed to stream tarball from {url}: {e}") from None
