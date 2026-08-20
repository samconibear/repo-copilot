from dataclasses import dataclass


class LoadError(Exception):
    """Raised when a source can't be loaded."""


@dataclass(frozen=True)
class SourceFile:
    """One file's content, independent of where it came from."""
    path: str  # POSIX-style, relative to the source root
    data: bytes  # raw file content