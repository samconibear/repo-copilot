"""
batching, header enrichment, and Ollama daemon
"""

import json
import urllib.error
import urllib.request
from typing import Iterable

from ..chunking.models import Chunk
from .models import EmbedConfig, EmbedError, Embedding

_EMBED_CONFIG = EmbedConfig(model="nomic-embed-text", dim=768)


def embed_chunks(
    chunks: list[Chunk], config: EmbedConfig = _EMBED_CONFIG
) -> list[Embedding]:
    return list(run(chunks, config))


def embed_query(text: str, config: EmbedConfig = _EMBED_CONFIG) -> list[float]:
    return _call_ollama([text], config)[0]


def run(
    chunks: Iterable[Chunk], config: EmbedConfig = _EMBED_CONFIG
) -> Iterable[Embedding]:
    batch: list[Chunk] = []
    batch_chars = 0
    for chunk in chunks:
        text = _enrich_with_header(chunk)
        if batch and (
            len(batch) >= config.batch_size or batch_chars + len(text) > config.max_batch_chars
        ):
            yield from _embed_batch(batch, config)
            batch, batch_chars = [], 0
        batch.append(chunk)
        batch_chars += len(text)
    if batch:
        yield from _embed_batch(batch, config)


def _embed_batch(batch: list[Chunk], config: EmbedConfig) -> list[Embedding]:
    texts = [_enrich_with_header(c) for c in batch]
    vectors = _call_ollama(texts, config)
    return [
        Embedding(key=c.key, file_path=c.file_path, vector=v, model=config.model, dim=len(v))
        for c, v in zip(batch, vectors)
    ]


def _call_ollama(texts: list[str], config: EmbedConfig) -> list[list[float]]:
    body = json.dumps({"model": config.model, "input": texts}).encode("utf-8")
    request = urllib.request.Request(
        config.base_url, data=body, method="POST", headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise EmbedError(f"Ollama API error {e.code}: {detail}") from None
    except urllib.error.URLError as e:
        raise EmbedError(
            f"failed to reach Ollama at {config.base_url} ({e.reason}) - "
            f"is `ollama serve` running and has `{config.model}` been pulled?"
        ) from None
    return payload["embeddings"]


def _enrich_with_header(chunk: Chunk) -> str:
    if chunk.chunk_type == "symbol":
        header = f"# {chunk.file_path} :: {chunk.symbol_kind} {chunk.qualified_name}"
    elif chunk.chunk_type == "gap":
        header = f"# {chunk.file_path} (module-level code)"
    else:  # "text"
        header = f"# {chunk.file_path}"
    return f"{header}\n{chunk.content}"
