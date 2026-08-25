"""HTTP interface (layer 9): a thin FastAPI wrapper over the two things a
caller does with a repo - ingest it, then ask questions against the agent
loop (layer 8). No new logic lives here; every endpoint just validates
input with a pydantic model and delegates.

Run with: uvicorn src.api.server.main:app --reload
"""

import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ...rag.embedding.models import EmbedError
from ...rag.ingest import ingest_repo_stream
from ...rag.loaders.models import LoadError
from ...rag.storage.engine import list_repos
from ...rag.storage.models import StoreError
from ..agent.loop import ask as agent_ask
from ..agent.models import AgentError

app = FastAPI(
    title="Repo Copilot API",
    description="Ingest a repo, then ask questions about it via an LLM agent.",
)


class IngestRequest(BaseModel):
    repo_source: str = Field(
        ..., min_length=1, description="GitHub URL or local path to ingest"
    )


class AskRequest(BaseModel):
    repo_source: str = Field(
        ..., min_length=1, description="GitHub URL or local path, already ingested"
    )
    question: str = Field(..., min_length=1)


class Citation(BaseModel):
    """One `search_code` result the agent used while answering - see
    plans/08-frontend.md decision #7/#8. Mirrors src/api/mcp/tools.py's
    `_result_to_dict` shape, minus the fields the frontend doesn't use
    (chunk_type, symbol_kind, parent)."""

    file_path: str
    start_line: int
    end_line: int
    qualified_name: str | None
    score: float
    content: str


class AskResponse(BaseModel):
    repo_source: str
    answer: str
    citations: list[Citation]


class RepoInfoResponse(BaseModel):
    repo_source: str
    chunks_ingested: int
    ingested_at: str


@app.get("/repos", response_model=list[RepoInfoResponse])
def repos() -> list[RepoInfoResponse]:
    """Every already-ingested repo, most recently ingested first - lets a
    caller list-and-select instead of re-entering a repo_source it's
    ingested before. See plans/09-repo-list.md."""
    return sorted(
        (RepoInfoResponse(**r.__dict__) for r in list_repos()),
        key=lambda r: r.ingested_at,
        reverse=True,
    )


@app.post("/ingest")
def ingest(request: IngestRequest) -> StreamingResponse:
    """Load, chunk, embed, and index a repo. Wipes and rebuilds that repo's
    index from scratch - safe to call again after the repo changes.

    Streams progress as newline-delimited JSON (one `dict` per line, see
    `ingest_repo_stream`'s docstring for the event shapes) instead of one
    blocking response - the embedding phase in particular can take a
    while, and every layer underneath already produces these numbers as
    it goes. The body always ends with exactly one terminal event, either
    {"phase": "done", "chunks_ingested": N} or {"phase": "error", "detail":
    "..."} - by the time ingestion can fail, the streaming response has
    already started (status 200, headers sent), so a caught error can't
    become an HTTP error status the way it could for a single blocking
    response; the terminal event is the only way it surfaces. See
    plans/10-ingest-progress.md."""

    def events():
        try:
            for event in ingest_repo_stream(request.repo_source):
                yield json.dumps(event) + "\n"
        except (LoadError, EmbedError, StoreError) as e:
            yield json.dumps({"phase": "error", "detail": str(e)}) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson")


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    """Answer a question about an already-ingested repo, running the same
    search_code/read_file/list_files tool loop as the MCP server."""
    try:
        result = agent_ask(request.repo_source, request.question)
    except AgentError as e:
        raise HTTPException(status_code=502, detail=str(e)) from None
    return AskResponse(
        repo_source=request.repo_source,
        answer=result.answer,
        citations=[Citation(**c) for c in result.citations],
    )
