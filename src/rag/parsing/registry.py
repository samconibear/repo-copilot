"""LANGUAGES table + language_for_path(). Only file that knows which
grammars/query files exist. Add lang: 1) LANGUAGE_EXTENSIONS entry in
../language_names.py, 2) LanguageConfig entry below, 3)
queries/<x>.scm using <base>.def/<base>.name convention (base =
func|method|class|interface|arrow, see engine.py).

extensions=LANGUAGE_EXTENSIONS[name] rather than a literal tuple here,
and language_for_path() below is a thin wrapper over
language_names.language_for_extension() rather than its own loop -
filtering.py calls that same shared function directly too, instead of
this module's language_for_path(). One lookup implementation, not two
copies that could drift; see ../language_names.py.

containers vs receiver_owner: see LanguageConfig docstring in models.py.

Per-lang notes, verified via testing not grammar docs:
- C: no containers, no method concept, fns never nest in structs.
- C++: member fn name node = field_identifier, top-level = identifier
  (cpp.scm uses (_) wildcard). Out-of-line defs (Point::distance()) use
  qualified_identifier declarator - not resolved to parent, known gap,
  still returned as unattributed function not dropped.
- Rust: impl_item owner field is "type" not "name".
- Go: method_declaration has own node type but NOT nested in struct -
  receiver is a field on the node itself, needs receiver_owner.

_go_receiver_owner must be defined before LANGUAGES (referenced inside
it, no hoisting in Python).
"""

from tree_sitter import Node

from ..language_names import LANGUAGE_EXTENSIONS, language_for_extension
from .models import LanguageConfig


def _go_receiver_owner(def_node: Node, source: bytes) -> str | None:
    """Go receiver: (p *Point) or (p Point). Unwrap pointer_type ->
    type_identifier if pointer receiver, else bare type_identifier.
    Verified both forms."""
    receiver = def_node.child_by_field_name("receiver")
    if receiver is None:
        return None
    param_decl = next(
        (c for c in receiver.children if c.type == "parameter_declaration"), None
    )
    if param_decl is None:
        return None
    type_node = param_decl.child_by_field_name("type")
    if type_node is None:
        return None
    if type_node.type == "pointer_type":
        type_node = next(
            (c for c in type_node.children if c.type == "type_identifier"), None
        )
    if type_node is None or type_node.type != "type_identifier":
        return None
    return source[type_node.start_byte : type_node.end_byte].decode(
        "utf-8", errors="replace"
    )


LANGUAGES: dict[str, LanguageConfig] = {
    "python": LanguageConfig(
        ts_name="python",
        query_file="python.scm",
        extensions=LANGUAGE_EXTENSIONS["python"],
        containers={"class_definition": "name"},
    ),
    "javascript": LanguageConfig(
        ts_name="javascript",
        query_file="javascript.scm",
        extensions=LANGUAGE_EXTENSIONS["javascript"],
        containers={"class_declaration": "name"},
    ),
    "typescript": LanguageConfig(
        ts_name="typescript",
        query_file="typescript.scm",
        extensions=LANGUAGE_EXTENSIONS["typescript"],
        containers={"class_declaration": "name"},
    ),
    "tsx": LanguageConfig(
        ts_name="tsx",
        query_file="typescript.scm",  # tsx grammar is superset of ts's
        extensions=LANGUAGE_EXTENSIONS["tsx"],
        containers={"class_declaration": "name"},
    ),
    "go": LanguageConfig(
        ts_name="go",
        query_file="go.scm",
        extensions=LANGUAGE_EXTENSIONS["go"],
        receiver_owner=_go_receiver_owner,  # not nested, no containers
    ),
    "rust": LanguageConfig(
        ts_name="rust",
        query_file="rust.scm",
        extensions=LANGUAGE_EXTENSIONS["rust"],
        containers={"impl_item": "type"},  # field is "type" not "name"
    ),
    "c": LanguageConfig(
        ts_name="c",
        query_file="c.scm",
        extensions=LANGUAGE_EXTENSIONS["c"],
        # no containers - fns never nest in structs, no method concept
    ),
    "cpp": LanguageConfig(
        ts_name="cpp",
        query_file="cpp.scm",
        extensions=LANGUAGE_EXTENSIONS["cpp"],
        containers={"class_specifier": "name", "struct_specifier": "name"},
    ),
}


assert LANGUAGES.keys() == LANGUAGE_EXTENSIONS.keys(), (
    "LANGUAGES (parsing/registry.py) and LANGUAGE_EXTENSIONS "
    "(language_names.py) must define the same language names - a name "
    "in LANGUAGE_EXTENSIONS with no LANGUAGES entry means filtering.py "
    "would classify a file as that language while parse_file() silently "
    "returns [] for it (no grammar registered), permanently dropping "
    "that file from the index with no error anywhere."
)


def language_for_path(path: str) -> str | None:
    """Ext -> lang name. Thin wrapper over language_names.
    language_for_extension() - kept as parsing's own public entrypoint
    (see parsing/__init__.py's __all__) so callers here don't need to
    know the actual lookup lives in the shared, layer-neutral module.
    LANGUAGES.keys() == LANGUAGE_EXTENSIONS.keys() and each
    LanguageConfig.extensions is literally that same table's value, so
    this returns identically to scanning LANGUAGES directly - confirmed
    by testing, not just asserted."""
    return language_for_extension(path)
