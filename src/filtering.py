from .language_names import language_for_extension
from .loaders.models import SourceFile

_EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".venv",
    "venv",
    "target",
    ".next",
    "coverage",
    ".idea",
    ".vscode",
}

_MAX_FILE_SIZE = 500_000  # bytes


def language_for_file(file: SourceFile) -> str | None:
    dir_parts = file.path.split("/")[:-1]
    if _EXCLUDED_DIRS & set(dir_parts):
        return None
    if len(file.data) > _MAX_FILE_SIZE:
        return None
    if b"\x00" in file.data[:8192]:  # cheap binary sniff
        return None
    return language_for_extension(file.path) or "text"
