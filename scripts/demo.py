"""Demo: ingest a repo and run one question through the same search_code
tool the MCP server exposes (src/mcp/tools.py), printing ranked, cited
results.

Run with: python -m scripts.demo [repo-source] [question]
Defaults to this project's own src/ and a question about the storage layer.
"""
import sys

from src import ingest
from src.embedding.models import EmbedError
from src.loaders.models import LoadError
from src.mcp import tools
from src.storage.models import StoreError

DEFAULT_REPO = "./src"
DEFAULT_QUESTION = "how does the storage layer save chunks and embeddings to sqlite?"


def main() -> None:
    repo_source = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_REPO
    question = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_QUESTION

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
