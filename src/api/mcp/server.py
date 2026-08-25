"""
MCP server
Run with: python -m src.api.mcp.server <github-url-or-local-path>

Ingestion is not triggered here - run `python -m scripts.ingest
<github-url-or-local-path>` first to build the index this server reads.
"""
import sys

from mcp.server import MCPServer

from . import tools

REPO_SOURCE: str | None = None

mcp = MCPServer(
    "repo-copilot",
    instructions=(
        "Exposes a search index built from one specific, already-ingested "
        "checkout of a repo (see the repo_source it was started with). "
        "For ANY question about that repo's implementation, behavior, "
        "structure, or code - including repos you recognize from training "
        "data - use these tools rather than answering from memory. This "
        "checkout may be a different version, fork, or have local "
        "modifications, so prior knowledge of the project may not match "
        "what is actually indexed here. Typical flow: search_code to find "
        "relevant chunks, then read_file on promising paths to see full, "
        "exact context before answering; list_files for structure/layout "
        "questions."
    ),
)


@mcp.tool()
def search_code(query: str, top_k: int = 10) -> list[dict]:
    """Semantic search over this repo's indexed code chunks - the primary,
    authoritative way to answer any question about how this specific
    codebase works. Always call this first for implementation/behavior
    questions about the repo, even for famous libraries you already know:
    the indexed checkout may differ from what you remember. Returns the
    top_k most similar chunks, each with file path, line range, chunk
    type, and a 0-1 similarity score (higher is better). Follow up with
    read_file on the most relevant paths before answering."""
    return tools.search_code(REPO_SOURCE, query, top_k)


@mcp.tool()
def read_file(path: str) -> str:
    """Read one indexed file's full, exact original content, given its
    path as returned by search_code or list_files. Use this to confirm
    or expand on a search_code hit before answering - chunks are partial;
    this is the ground truth for a whole file."""
    return tools.read_file(REPO_SOURCE, path)


@mcp.tool()
def list_files() -> list[str]:
    """List every file path indexed for this repo. Use this for
    structure/layout questions ("what's in this repo", "where are the
    tests") or to find a path before calling read_file."""
    return tools.list_files(REPO_SOURCE)


def main() -> None:
    global REPO_SOURCE
    if len(sys.argv) != 2:
        print("usage: python -m src.api.mcp.server <github-url-or-local-path>", file=sys.stderr)
        raise SystemExit(1)
    REPO_SOURCE = sys.argv[1]

    print("serving over stdio", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
