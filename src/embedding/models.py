from dataclasses import dataclass


class EmbedError(Exception):
    """Raised when embedding a batch fails"""


@dataclass(frozen=True)
class EmbedConfig:
    """model/batch settings for the embedding call"""
    model: str
    dim: int # output vector width
    batch_size: int = 64
    max_batch_chars: int = 200_000  # ~4 chars/token approx,
    base_url: str = "http://localhost:11434/api/embed"


@dataclass(frozen=True)
class Embedding:
    key: str
    file_path: str
    vector: list[float]
    model: str
    dim: int
