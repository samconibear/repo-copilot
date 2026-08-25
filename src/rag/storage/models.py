from dataclasses import dataclass

from ..chunking.models import Chunk


class StoreError(Exception):
    """Raised when ingest()/search() fails"""


@dataclass(frozen=True)
class SearchResult:
    chunk: Chunk
    score: float


@dataclass(frozen=True)
class RepoInfo:
    """One row of the `meta` table - the human-readable identity of an
    indexed repo, since the .db filename itself (slug + hash) isn't
    reversible back to the original repo_source. See
    plans/09-repo-list.md."""

    repo_source: str
    chunks_ingested: int
    ingested_at: str  # UTC ISO 8601
