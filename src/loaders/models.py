from dataclasses import dataclass


class LoadError(Exception):
    """Raised when a source can't be loaded."""


@dataclass(frozen=True)
class SourceFile:
    path: str  # POSIX-style, relative to the source root
    data: bytes