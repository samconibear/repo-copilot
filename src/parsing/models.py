"""Symbol = parse_file() output, language-agnostic. LanguageConfig =
per-language config schema, instances in registry.py.
"""

from dataclasses import dataclass, field
from typing import Callable

from tree_sitter import Node


class ParseError(Exception):
    """Only for genuine parser failure. Not raised for unknown language
    or zero symbols found - those return []."""


@dataclass(frozen=True)
class LanguageConfig:
    """
    ts_name: tree_sitter_language_pack language id.
    query_file: .scm under queries/, shared across langs w/ matching
      capture shape (e.g. typescript+tsx).
    extensions: file extensions owned by this lang.
    containers: {ancestor_node_type: field_name_for_owner_name}. For
      langs where method nests in class body (Python, JS/TS, Rust,
      C++). Field name varies per lang - Rust impl_item uses "type" not
      "name", verified not assumed.
    receiver_owner: fn(def_node, source)->owner_name|None. For langs
      where method ISN'T nested (Go - receiver is a field on the method
      node itself). Tried only if containers finds nothing.
    """

    ts_name: str
    query_file: str
    extensions: tuple[str, ...]
    containers: dict[str, str] = field(default_factory=dict)
    receiver_owner: Callable[[Node, bytes], str | None] | None = None


@dataclass(frozen=True)
class Symbol:
    """
    kind: function|method|class|interface. method vs function decided
      in engine.py via LanguageConfig.containers/receiver_owner, not
      read directly off the query capture.
    qualified_name: "{parent}.{name}" or just name.
    start/end_line: 1-indexed inclusive (tree-sitter is 0-indexed,
      engine.py adds 1).
    start/end_byte: exact offsets into source bytes.
    signature: first line of def only, not full multi-line signature.
    parent: owning class/struct name or None.
    source: full text of the def node.
    """

    file_path: str
    kind: str
    name: str
    qualified_name: str
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int
    signature: str
    parent: str | None
    source: str
