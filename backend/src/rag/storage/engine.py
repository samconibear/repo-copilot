import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import apsw
import sqlite_vec

from ..chunking.models import Chunk
from ..embedding.models import Embedding
from ..loaders.models import SourceFile
from .models import RepoInfo, SearchResult, StoreError

# backend root: backend/src/rag/storage/engine.py -> parents[3]. (Was
# parents[2] back when this module lived at src/storage/engine.py, one level
# shallower - fixed as part of plans/09-repo-list.md; the stale `data/store/`
# content left behind by that bug is *not* touched here, see that doc. Stayed
# at parents[3] when `src/` moved under `backend/` - the added directory
# level now resolves to <backend-root>/data/store instead of <repo-root>,
# which is what we want: backend owns its own data, same as frontend/dist.)
DEFAULT_ROOT = Path(__file__).resolve().parents[3] / "data" / "store"

_VEC_DIM = 768 # need to expose in future if change embed model

_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS chunks (
    key TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    content TEXT NOT NULL,
    chunk_type TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    qualified_name TEXT,
    symbol_kind TEXT,
    parent TEXT,
    part INTEGER,
    part_count INTEGER
);
CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
    key TEXT PRIMARY KEY,
    embedding FLOAT[{_VEC_DIM}] distance_metric=cosine
);
CREATE TABLE IF NOT EXISTS files (
    file_path TEXT PRIMARY KEY,
    content TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (
    repo_source TEXT NOT NULL,
    chunks_ingested INTEGER NOT NULL,
    ingested_at TEXT NOT NULL
);
"""


def ingest(repo_source: str, chunks: Iterable[Chunk], embeddings: Iterable[Embedding]) -> int:
    chunks = list(chunks)
    embeddings = list(embeddings)
    if len(chunks) != len(embeddings):
        raise StoreError(
            f"chunks/embeddings length mismatch: {len(chunks)} vs {len(embeddings)}"
        )

    conn = _connect(repo_source)
    try:
        with conn:
            conn.execute("DELETE FROM chunks")
            conn.execute("DELETE FROM vec_chunks")
            conn.execute("DELETE FROM meta")
            conn.execute(
                "INSERT INTO meta (repo_source, chunks_ingested, ingested_at) VALUES (?, ?, ?)",
                (repo_source, len(chunks), datetime.now(timezone.utc).isoformat()),
            )
            for chunk, emb in zip(chunks, embeddings):
                if chunk.key != emb.key:
                    raise StoreError(
                        f"chunk/embedding key mismatch: {chunk.key!r} vs {emb.key!r}"
                    )
                if emb.dim != _VEC_DIM:
                    raise StoreError(
                        f"embedding dim {emb.dim} ({emb.model}) != table dim {_VEC_DIM} - "
                        f"a model/dim change needs a new table, see plans/06-storage.md decision #2"
                    )
                conn.execute(
                    "INSERT INTO chunks (key, file_path, content, chunk_type, start_line, "
                    "end_line, qualified_name, symbol_kind, parent, part, part_count) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        chunk.key,
                        chunk.file_path,
                        chunk.content,
                        chunk.chunk_type,
                        chunk.start_line,
                        chunk.end_line,
                        chunk.qualified_name,
                        chunk.symbol_kind,
                        chunk.parent,
                        chunk.part,
                        chunk.part_count,
                    ),
                )
                conn.execute(
                    "INSERT INTO vec_chunks (key, embedding) VALUES (?, ?)",
                    (emb.key, sqlite_vec.serialize_float32(emb.vector)),
                )
    except apsw.Error as e:
        raise StoreError(f"failed to ingest into {_db_path(repo_source)}: {e}") from None
    finally:
        conn.close()
    return len(chunks)


def search(repo_source: str, query_vector: list[float], top_k: int = 10) -> list[SearchResult]:
    """Top-k cosine similarity search"""
    path = _db_path(repo_source)
    if not path.exists():
        raise StoreError(f"no index for {repo_source!r} at {path} - run ingestion first")

    conn = _connect(repo_source)
    try:
        rows = list(
            conn.execute(
                """
                SELECT c.key, c.file_path, c.content, c.chunk_type, c.start_line, c.end_line,
                       c.qualified_name, c.symbol_kind, c.parent, c.part, c.part_count,
                       v.distance
                FROM vec_chunks v
                JOIN chunks c ON c.key = v.key
                WHERE v.embedding MATCH ? AND v.k = ?
                ORDER BY v.distance
                """,
                (sqlite_vec.serialize_float32(query_vector), top_k),
            )
        )
    except apsw.Error as e:
        raise StoreError(f"failed to search {path}: {e}") from None
    finally:
        conn.close()

    return [
        SearchResult(
            chunk=Chunk(
                key=r[0],
                file_path=r[1],
                content=r[2],
                chunk_type=r[3],
                start_line=r[4],
                end_line=r[5],
                qualified_name=r[6],
                symbol_kind=r[7],
                parent=r[8],
                part=r[9],
                part_count=r[10],
            ),
            score=1.0 - r[11],
        )
        for r in rows
    ]


def ingest_files(repo_source: str, files: Iterable[SourceFile]) -> int:
    """Wipes and reinserts this repo's `files` table"""
    files = list(files)
    conn = _connect(repo_source)
    try:
        with conn:
            conn.execute("DELETE FROM files")
            for f in files:
                conn.execute(
                    "INSERT INTO files (file_path, content) VALUES (?, ?)",
                    (f.path, f.data.decode("utf-8", errors="replace")),
                )
    except apsw.Error as e:
        raise StoreError(f"failed to ingest files into {_db_path(repo_source)}: {e}") from None
    finally:
        conn.close()
    return len(files)


def read_file(repo_source: str, path: str) -> str:
    db_path = _db_path(repo_source)
    if not db_path.exists():
        raise StoreError(f"no index for {repo_source!r} at {db_path} - run ingestion first")

    conn = _connect(repo_source)
    try:
        row = conn.execute(
            "SELECT content FROM files WHERE file_path = ?", (path,)
        ).fetchone()
    except apsw.Error as e:
        raise StoreError(f"failed to read {path!r} from {db_path}: {e}") from None
    finally:
        conn.close()

    if row is None:
        raise StoreError(f"{path!r} is not an indexed file in {repo_source!r}")
    return row[0]


def list_files(repo_source: str) -> list[str]:
    db_path = _db_path(repo_source)
    if not db_path.exists():
        raise StoreError(f"no index for {repo_source!r} at {db_path} - run ingestion first")

    conn = _connect(repo_source)
    try:
        rows = list(conn.execute("SELECT file_path FROM files ORDER BY file_path"))
    except apsw.Error as e:
        raise StoreError(f"failed to list files in {db_path}: {e}") from None
    finally:
        conn.close()
    return [r[0] for r in rows]


def list_repos(root: Path = DEFAULT_ROOT) -> list[RepoInfo]:
    """Every indexed repo's `meta` row, one per `*.db` file under `root`.
    A `.db` with no readable `meta` row (e.g. ingested before this table
    existed) is skipped, not raised on - see plans/09-repo-list.md."""
    if not root.exists():
        return []

    repos = []
    for db_path in sorted(root.glob("*.db")):
        try:
            conn = _connect_at(db_path)
            try:
                row = conn.execute(
                    "SELECT repo_source, chunks_ingested, ingested_at FROM meta LIMIT 1"
                ).fetchone()
            finally:
                conn.close()
        except apsw.Error:
            continue
        if row is not None:
            repos.append(RepoInfo(repo_source=row[0], chunks_ingested=row[1], ingested_at=row[2]))
    return repos


def _connect(repo_source: str) -> apsw.Connection:
    path = _db_path(repo_source)
    path.parent.mkdir(parents=True, exist_ok=True)
    return _connect_at(path)


def _connect_at(path: Path) -> apsw.Connection:
    conn = apsw.Connection(str(path))
    conn.enableloadextension(True)
    conn.loadextension(sqlite_vec.loadable_path())
    conn.enableloadextension(False)
    conn.execute(_SCHEMA)
    return conn


def _db_path(repo_source: str, root: Path = DEFAULT_ROOT) -> Path:
    digest = hashlib.sha256(repo_source.encode("utf-8")).hexdigest()[:8]
    return root / f"{_slugify(repo_source)}-{digest}.db"


def _slugify(source: str) -> str:
    name = source.rstrip("/")
    name = re.sub(r"\.git$", "", name)
    name = name.rsplit("/", 1)[-1]
    name = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    return name or "repo"
