"""parse_file(path, language, source_bytes) -> list[Symbol]. Only file
touching tree-sitter API directly. Never branches per-language - reads
LanguageConfig fields only.

Query capture convention: <base>.def / <base>.name, base in
func/method/class/interface/arrow. _CAPTURE_KIND maps base->default kind.

Uses cursor.matches() not cursor.captures(): matches() groups def/name
per pattern match (list[(idx, {capture:[Node]})]); captures() returns
one flat dict for whole tree, would need fragile index-pairing across
multiple matches of same pattern.

kind=method + parent not read from capture alone. _resolve_owner()
checks LanguageConfig.containers (ancestor walk) then receiver_owner
(Go-style, non-nested). See models.py LanguageConfig docstring.
"""

from functools import lru_cache
from pathlib import Path

from tree_sitter import Node, Query, QueryCursor
from tree_sitter_language_pack import get_language, get_parser

from .models import ParseError, Symbol
from .registry import LANGUAGES, LanguageConfig

_QUERIES_DIR = Path(__file__).parent / "queries"

_CAPTURE_KIND = {
    "func": "function",
    "method": "method",
    "class": "class",
    "interface": "interface",
    "arrow": "function",
}

_SCOPED_BASES = {"func", "method", "arrow"}  # eligible for method upgrade + parent


@lru_cache(maxsize=None)
def _load_query(ts_name: str, query_file: str) -> Query:
    # cached on strings not LanguageConfig - containers dict unhashable
    query_src = (_QUERIES_DIR / query_file).read_text()
    language = get_language(ts_name)
    return Query(language, query_src)


def parse_file(path: str, language: str, source: bytes) -> list[Symbol]:
    """[] if no grammar for `language` or zero matches. ParseError only
    on actual tree-sitter parser failure - malformed source doesn't
    raise, tree-sitter is error-tolerant, partial tree still queried."""
    config = LANGUAGES.get(language)
    if config is None:
        return []

    try:
        parser = get_parser(config.ts_name)
        tree = parser.parse(source)
    except Exception as e:
        raise ParseError(f"failed to parse '{path}' as {language}: {e}") from e

    query = _load_query(config.ts_name, config.query_file)
    cursor = QueryCursor(query)
    matches = cursor.matches(tree.root_node)

    symbols: list[Symbol] = []
    for _pattern_index, captures in matches:
        for base, kind in _CAPTURE_KIND.items():
            def_nodes = captures.get(f"{base}.def")
            name_nodes = captures.get(f"{base}.name")
            if not def_nodes or not name_nodes:
                continue
            symbols.append(
                _build_symbol(path, base, kind, def_nodes[0], name_nodes[0], source, config)
            )
    return symbols


def _build_symbol(
    path: str,
    base: str,
    kind: str,
    def_node: Node,
    name_node: Node,
    source: bytes,
    config: LanguageConfig,
) -> Symbol:
    name = _text(name_node, source)
    parent = None

    if base in _SCOPED_BASES:
        parent = _resolve_owner(def_node, config, source)
        if parent is not None:
            kind = "method"

    qualified_name = f"{parent}.{name}" if parent else name
    full_text = _text(def_node, source)
    signature = full_text.split("\n", 1)[0].rstrip()  # first line only

    return Symbol(
        file_path=path,
        kind=kind,
        name=name,
        qualified_name=qualified_name,
        start_line=def_node.start_point[0] + 1,  # 0->1 indexed
        end_line=def_node.end_point[0] + 1,
        start_byte=def_node.start_byte,
        end_byte=def_node.end_byte,
        signature=signature,
        parent=parent,
        source=full_text,
    )


def _resolve_owner(def_node: Node, config: LanguageConfig, source: bytes) -> str | None:
    """Ancestor-walk via containers first, then receiver_owner fallback.
    None = top-level, or lang has no owner mechanism configured (C)."""
    current = def_node.parent
    while current is not None:
        name_field = config.containers.get(current.type)
        if name_field is not None:
            name_node = current.child_by_field_name(name_field)
            if name_node is not None:
                return _text(name_node, source)
        current = current.parent

    if config.receiver_owner is not None:
        return config.receiver_owner(def_node, source)

    return None


def _text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")
