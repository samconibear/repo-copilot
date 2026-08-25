"""Demo: ingest a repo and run one question through the same search_code
tool the MCP server exposes (src/mcp/tools.py), printing ranked, cited
results.

Run with: python -m scripts.demo [query] [--repo REPO]
Defaults to this project's own src/ and a question about the storage layer.
"""
import argparse
import sys

from src.api.mcp import tools
from src.rag import ingest
from src.rag.embedding.models import EmbedError
from src.rag.loaders.models import LoadError
from src.rag.storage.models import StoreError

DEFAULT_REPO = "./src"
DEFAULT_QUESTION = "how does the storage layer save chunks and embeddings to sqlite?"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", default=DEFAULT_QUESTION, help="search query")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="repo source to ingest")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_source = args.repo
    question = args.query

    print(f"ingesting {repo_source} ...")
    try:
        n = ingest.ingest_repo(repo_source)
    except (LoadError, EmbedError, StoreError) as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(1) from None
    print(f"ingested {n} chunks\n")

    print(f"> {question}\n")
    results = tools.search_code(repo_source, question, top_k=5)
    for r in results:
        loc = f"{r['file_path']}:{r['start_line']}-{r['end_line']}"
        name = r.get("qualified_name") or ""
        print(f"[{r['score']:.3f}]  {loc}  {name}")
        snippet = r["content"].strip().splitlines()
        for line in snippet[:4]:
            print(f"    {line}")
        if len(snippet) > 4:
            print("    ...")
        print()


if __name__ == "__main__":
    main()
