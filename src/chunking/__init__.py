"""Chunking - turns Symbols (+ raw file bytes) into Chunk records, the
retrieval unit layer 5 (Embedding) operates on. See plans/04-chunking.md
for the full design log.

models.py    Chunk (output type), ChunkConfig (size-threshold schema)
registry.py  CHUNK_CONFIGS table - "default" only; per-model configs are
             layer 5's concern, not this package's (decision #8)
engine.py    chunk_symbols()/chunk_text()/run() - only file that knows
             the windowing/gap-splitting algorithm

Depends on repo_sage.filtering (language_for_file) and
repo_sage.parsing (Symbol, parse_file) - see "Position in the pipeline"
in plans/04-chunking.md.
"""

from .engine import chunk_symbols, chunk_text, run
from .models import Chunk, ChunkConfig
from .registry import CHUNK_CONFIGS

__all__ = [
    "CHUNK_CONFIGS",
    "Chunk",
    "ChunkConfig",
    "chunk_symbols",
    "chunk_text",
    "run",
]
