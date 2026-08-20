from dataclasses import dataclass

from ..chunking.models import Chunk


class StoreError(Exception):
    """Raised when ingest()/search() fails"""


@dataclass(frozen=True)
class SearchResult:
    chunk: Chunk
    score: float
