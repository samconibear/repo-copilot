"""CHUNK_CONFIGS table. Only "default" exists today - a fallback for
standalone/CLI use, not a per-embedding-model registry.

Deliberately not a `model name -> ChunkConfig` mapping: this package
doesn't know embedding models exist (see plans/04-chunking.md decision
#8's "deliberate layering choice"). Layer 5 (Embedding) owns that
mapping and passes a ChunkConfig in like any other caller - it may
build on this table, or keep its own, but this file isn't where a new
embedding model's config gets registered.
"""

from .models import ChunkConfig

CHUNK_CONFIGS: dict[str, ChunkConfig] = {
    "default": ChunkConfig(
        split_threshold=4000, window_size=2000, window_overlap=400, gap_min_size=40
    ),
}
