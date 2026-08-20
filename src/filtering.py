"""File Walking & Filtering — decides which files a Loader yields are
worth AST-parsing, and which language to parse them as.

Not a Loader concern (a Loader's job is just "hand back every file");
not a parsing concern (parse_file() shouldn't have to know about
node_modules). This is the connective layer plans/00-overview.md calls
layer 3, sitting directly on the Loader's stream — no Store involved.

Calls language_names.language_for_extension() rather than
parsing.registry.language_for_path() — same underlying lookup (parsing
wraps the same function, see registry.py), but reached via the shared,
layer-neutral module instead of by importing parsing's code directly.
See plans/00-overview.md's "Layer independence" note for why that
distinction matters. Keep it that way if this file changes — don't
reintroduce a direct `from .parsing...` import here.
"""

from __future__ import annotations

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

# Generated/minified/vendored files this size or larger aren't worth
# parsing — they're rarely hand-written code a user would ask about, and
# large files cost disproportionately more parse time for little value.
_MAX_FILE_SIZE = 500_000  # bytes


def language_for_file(file: SourceFile) -> str | None:
    """Tri-state: a registered language name, "text" (no grammar but
    passed every gate below - fallback-chunking eligible, see
    chunking.chunk_text), or None (skip entirely). No extension
    allowlist for "text" - the gates below already prove it's readable,
    non-excluded content; that's what makes Dockerfile/Makefile/LICENSE
    (no matching extension, still real text) chunkable without a
    maintained list (plans/04-chunking.md, decision #4)."""
    dir_parts = file.path.split("/")[:-1]
    if _EXCLUDED_DIRS & set(dir_parts):
        return None
    if len(file.data) > _MAX_FILE_SIZE:
        return None
    if b"\x00" in file.data[:8192]:  # cheap binary sniff
        return None
    return language_for_extension(file.path) or "text"
