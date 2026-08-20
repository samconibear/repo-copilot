from pathlib import Path
from typing import Iterable

from .models import LoadError, SourceFile

_ALWAYS_EXCLUDED_DIRS = { ".git" }

def walk_directory(root: Path) -> Iterable[SourceFile]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if _ALWAYS_EXCLUDED_DIRS & set(rel_parts):
            continue
        rel = path.relative_to(root).as_posix()
        yield SourceFile(path=rel, data=path.read_bytes())

class LocalLoader:
    """
    Implements Loader
    Loads source from a directory that already exists on disk.
    """
    def __init__(self, path: str | Path):
        self._path = Path(path)

    def load(self) -> Iterable[SourceFile]:
        if not self._path.is_dir():
            raise LoadError(f"'{self._path}' is not an existing local directory")
        yield from walk_directory(self._path.resolve())
