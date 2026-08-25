from typing import Iterator

from .chunking.engine import run as chunk_run
from .chunking.models import ChunkConfig
from .chunking.registry import CHUNK_CONFIGS
from .embedding.engine import embed_chunks
from .embedding.engine import run as embed_run
from .loaders.base import Loader
from .loaders.git import GitLoader
from .loaders.local import LocalLoader
from .storage import engine as storage

# How often to emit a progress event during loading/chunking - both phases
# have no known total ahead of time, so events are just a running counter,
# and firing one per item would be excessive event volume for a large repo.
# Embedding needs no equivalent constant: it already yields per-batch
# (up to embed.EmbedConfig.batch_size items), a naturally coarse cadence.
_PROGRESS_EVERY = 25


def loader_for(source: str) -> Loader:
    return (
        GitLoader(source)
        if source.startswith(("http://", "https://", "git@"))
        else LocalLoader(source)
    )


def ingest_repo(repo_source: str, config: ChunkConfig = CHUNK_CONFIGS["default"]) -> int:
    """Blocking: load, chunk, embed, and index a repo, returning the chunk
    count once every step is done. No progress feedback - for callers that
    just want the end result (CLI scripts). See `ingest_repo_stream` for
    the progress-emitting equivalent used by the HTTP layer."""
    files = list(loader_for(repo_source).load())
    chunks = list(chunk_run(files, config))
    embeddings = embed_chunks(chunks)
    storage.ingest(repo_source, chunks, embeddings)
    storage.ingest_files(repo_source, files)
    return len(chunks)


def ingest_repo_stream(
    repo_source: str, config: ChunkConfig = CHUNK_CONFIGS["default"]
) -> Iterator[dict]:
    """Same four steps as `ingest_repo`, as a generator yielding progress
    events instead of returning once at the end. Every event is a dict
    with a "phase" key:

    - {"phase": "loading", "files_loaded": N}      - no total available yet
    - {"phase": "chunking", "chunks_produced": N}   - no total available yet
    - {"phase": "embedding", "chunks_embedded": N, "chunks_total": M} - a
      real fraction: the chunk count is known once chunking finishes
    - {"phase": "storing"}
    - {"phase": "done", "chunks_ingested": N}       - terminal, success

    Deliberately separate from `ingest_repo` rather than one calling the
    other: keeping `ingest_repo` calling `chunk_run`/`embed_chunks` (list
    in, list out) unchanged means its existing tests keep testing real
    behavior, not a drained stream - see plans/10-ingest-progress.md
    decision #1. The two share `loader_for`/`chunk_run`/`storage` and
    differ only in how the embedding step is driven (`embed_chunks`
    wraps `run()` in a `list()`; here `run()` is iterated directly for
    its per-batch yields) and in collecting vs. yielding progress.
    """
    files: list = []
    yield {"phase": "loading", "files_loaded": 0}
    for f in loader_for(repo_source).load():
        files.append(f)
        if len(files) % _PROGRESS_EVERY == 0:
            yield {"phase": "loading", "files_loaded": len(files)}
    yield {"phase": "loading", "files_loaded": len(files)}

    chunks = []
    yield {"phase": "chunking", "chunks_produced": 0}
    for c in chunk_run(files, config):
        chunks.append(c)
        if len(chunks) % _PROGRESS_EVERY == 0:
            yield {"phase": "chunking", "chunks_produced": len(chunks)}
    yield {"phase": "chunking", "chunks_produced": len(chunks)}

    total_chunks = len(chunks)
    embeddings = []
    yield {"phase": "embedding", "chunks_embedded": 0, "chunks_total": total_chunks}
    for emb in embed_run(chunks):
        embeddings.append(emb)
        yield {
            "phase": "embedding",
            "chunks_embedded": len(embeddings),
            "chunks_total": total_chunks,
        }

    yield {"phase": "storing"}
    storage.ingest(repo_source, chunks, embeddings)
    storage.ingest_files(repo_source, files)
    yield {"phase": "done", "chunks_ingested": len(chunks)}
