"""Standalone ingestion: index a repo without starting the MCP server or
agent CLI. Useful for pre-warming the index, re-ingesting after the repo
changes, or running ingestion in CI/cron separate from serving.

Run with: python -m scripts.ingest <github-url-or-local-path>
"""
import sys

from src.rag import ingest
from src.rag.embedding.models import EmbedError
from src.rag.loaders.models import LoadError
from src.rag.storage.models import StoreError


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python -m scripts.ingest <github-url-or-local-path>", file=sys.stderr)
        raise SystemExit(1)
    repo_source = sys.argv[1]

    print(f"ingesting {repo_source}...", file=sys.stderr)
    try:
        n = ingest.ingest_repo(repo_source)
    except (LoadError, EmbedError, StoreError) as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(1) from None
    print(f"ingested {n} chunks", file=sys.stderr)


if __name__ == "__main__":
    main()
