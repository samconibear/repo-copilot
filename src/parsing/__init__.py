"""AST parsing (tree-sitter). Languages: python/js/ts/tsx/go/rust/c/cpp.
Add lang = registry.py entry + queries/<x>.scm, no code change elsewhere.

models.py    Symbol (output type), LanguageConfig (per-lang schema)
registry.py  LANGUAGES table, language_for_path() - edit here to add lang
engine.py    parse_file() - only file using tree-sitter API directly
queries/     one .scm per lang, shared capture convention <base>.def/.name

No file I/O in this package. repo_sage/filtering.py picks language +
files, repo_sage/pipeline.py streams Loader -> filter -> parse_file(),
no Store involved.
"""

from .engine import parse_file
from .models import ParseError, Symbol
from .registry import LANGUAGES, LanguageConfig, language_for_path

__all__ = [
    "LANGUAGES",
    "LanguageConfig",
    "ParseError",
    "Symbol",
    "language_for_path",
    "parse_file",
]
