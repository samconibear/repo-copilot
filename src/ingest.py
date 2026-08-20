from .chunking.engine import run as chunk_run
from .chunking.models import ChunkConfig
from .chunking.registry import CHUNK_CONFIGS
from .embedding.engine import embed_chunks
from .loaders.base import Loader
from .loaders.git import GitLoader
from .loaders.local import LocalLoader
from .storage import engine as storage


def loader_for(source: str) -> Loader:
    return (
        GitLoader(source)
        if source.startswith(("http://", "https://", "git@"))
        else LocalLoader(source)
    )


def ingest_repo(repo_source: str, config: ChunkConfig = CHUNK_CONFIGS["default"]) -> int:
    files = list(loader_for(repo_source).load())
    chunks = list(chunk_run(files, config))
    embeddings = embed_chunks(chunks)
    storage.ingest(repo_source, chunks, embeddings)
    storage.ingest_files(repo_source, files)
    return len(chunks)
