"""Anthropic tool schemas. Wraps the mcp/tools.py"""

from ..mcp import tools as impl

TOOL_SCHEMAS = [
    {
        "name": "search_code",
        "description": (
            "Semantic search over this repo's indexed code chunks - the primary,"
            "authoritative way to answer any question about how this specific"
            "codebase works. Always call this first for implementation/behavior"
            "questions about the repo, even for famous libraries you already know:"
            "the indexed checkout may differ from what you remember. Returns the"
            "top_k most similar chunks, each with file path, line range, chunk"
            "type, and a 0-1 similarity score (higher is better). Follow up with"
            "read_file on the most relevant paths before answering."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "natural-language search query"},
                "top_k": {"type": "integer", "description": "number of results, default 10"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_file",
        "description": (
            "Read one indexed file's full, exact original content, given its"
            "path as returned by search_code or list_files. Use this to confirm"
            "or expand on a search_code hit before answering - chunks are partial"
            "this is the ground truth for a whole file."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "list_files",
        "description": "List every file path indexed for this repo.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def dispatch(repo_source: str, name: str, tool_input: dict) -> object:
    if name == "search_code":
        return impl.search_code(repo_source, tool_input["query"], tool_input.get("top_k", 10))
    if name == "read_file":
        return impl.read_file(repo_source, tool_input["path"])
    if name == "list_files":
        return impl.list_files(repo_source)
    raise ValueError(f"unknown tool: {name}")
