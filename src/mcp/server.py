"""
MCP server 
Run with: python -m src.mcp.server <github-url-or-local-path>
"""
import sys

from mcp.server import MCPServer

from . import tools

REPO_SOURCE: str | None = None

mcp = MCPServer("repo-copilot")


@mcp.tool()
def search_code(query: str, top_k: int = 10) -> list[dict]:
    """Semantic search over this repo's indexed code chunks. Returns
    the top_k most similar chunks, each with file path, line range,
    chunk type, and a 0-1 similarity score (higher is better)."""
    return tools.search_code(REPO_SOURCE, query, top_k)


@mcp.tool()
def read_file(path: str) -> str:
    """Read one indexed file's full, exact original content, given its
    path as returned by search_code or list_files."""
    return tools.read_file(REPO_SOURCE, path)


@mcp.tool()
def list_files() -> list[str]:
    """List every file path indexed for this repo."""
    return tools.list_files(REPO_SOURCE)


def main() -> None:
    global REPO_SOURCE
    if len(sys.argv) != 2:
        print("usage: python -m src.mcp.server <github-url-or-local-path>", file=sys.stderr)
        raise SystemExit(1)
    REPO_SOURCE = sys.argv[1]
    mcp.run()


if __name__ == "__main__":
    main()
