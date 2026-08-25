# Repo-Copilot
This repo exposes a codebase as an MCP server: point it at a repo (a GitHub URL or a local path) and it serves three tools — `search_code`, `read_file`,
`list_files` - over MCP. The server itself never ingests - build the index
first with `scripts.ingest` (see below), then point the server at the same repo.

## Prerequisites

- **Python 3.14.6** ([.python-version](backend/.python-version)). If you use `pyenv`:
  ```bash
  pyenv install 3.14.6
  ```
- **Ollama**, running locally with the `nomic-embed-text` model pulled 
  Install from [ollama.com](https://ollama.com) or `brew install ollama`, then:
  ```bash
  ollama pull nomic-embed-text
  ```
  Ollama needs to be running (`ollama serve`, or the desktop app) before you
  start the server.



## Quick Start

#### Backend:
```bash
# Install deps
cd backend
python3.14 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

# Make sure Ollama is running (see Prerequisites)
ollama serve

# Make sure your anthropic api key is defined
export ANTHROPIC_API_KEY="your_api_key"

# Start the API (from backend/, with .venv activated)
uvicorn src.api.server.main:app --reload
```

#### Frontend:
```bash
# Start the frontend (separate terminal)
cd frontend
npm install
npm run dev
```
The frontend then talks to the API at `http://localhost:8000`.


## Running tests

### Backend:
```bash
cd backend
. .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

### Frontend:
```bash
cd frontend
npm install   # if not already installed
npm test
```

## Ingest a repo

You can also manually ingest a repo (run from `backend/`, with `.venv` activated):

```bash
python -m scripts.ingest <github-url-or-local-path>
# e.g.
python -m scripts.ingest https://github.com/owner/repo
python -m scripts.ingest ./path/to/local/repo
```

Every run wipes and re-ingests that repo's index from scratch, there's no incremental/cached ingestion yet.

## Run it standalone

Once a repo has been ingested, point the server at the same repo (run from `backend/`):

```bash
python -m src.api.mcp.server <github-url-or-local-path>
# e.g.
python -m src.api.mcp.server https://github.com/owner/repo
python -m src.api.mcp.server ./path/to/local/repo
```

## Connect an MCP client
The server speaks MCP over **stdio**. For Claude Code:

```bash
claude mcp add repo-copilot -- python -m src.api.mcp.server <github-url-or-local-path>
```
(run from this repo's `backend/` directory, with `.venv` activated, or use
the venv's absolute Python path, e.g.
`/path/to/codebase-copilot/backend/.venv/bin/python`).

For Claude Desktop, add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "repo-copilot": {
      "command": "/absolute/path/to/codebase-copilot/backend/.venv/bin/python",
      "args": ["-m", "src.api.mcp.server", "<github-url-or-local-path>"],
      "cwd": "/absolute/path/to/codebase-copilot/backend",
      "env": {
        "PYTHONPATH": "/absolute/path/to/codebase-copilot/backend"
      }
    }
  }
}
```

## HTTP API

- `POST /ingest` — `{"repo_source": "<github-url-or-local-path>"}` ->
  indexes the repo (wipe-and-rebuild, same as `scripts.ingest`).
- `POST /ask` — `{"repo_source": ..., "question": "..."}` -> uns the same
  agent loop as the MCP server (`search_code`/`read_file`/`list_files`
  tools) and returns `{"repo_source": ..., "answer": "..."}`. Requires
  `ANTHROPIC_API_KEY` in the environment.

---

# Design choices

Before designing the system, I set out a few goals for how I wanted the system to be architected:

1. Use a micro-services like architecture, for 2 reasons:
  
  a. This makes it easier to modify the individual "layers" of the application later.
  
  b. For a scalable, production grade, event-driven application, different components will need to be placed in different serverless compute, along side this, it would likely be optimal to run different layers in managed queues (such as the embedding layer, which will have a token per minute (TPM) quota)

In practice that means no layer is dependant on the logic of another layer, they could be deployed on independent compute.

| LAYER | PURPOSE |
|-------|---------|
|1      | Loading source code files |
|2      | Filter/walk files, language detection |
|3      | Parse each file into AST symbols |
|4      | Chunk oversized symbols and non code files |
|5      | Embedding - generate vectors from code symbols |
|6      | Storage of vectors and metadata |
|7      | Tools - `search_code`/`read_file`/`list_files`, exposed over MCP |
|8      | Agent loop - LLM-driven tool-calling over the tools layer |
|9      | HTTP API - FastAPI wrapper over ingestion + the agent loop |
|10     | Frontend - React/Tailwind chat UI over the HTTP API |

---

# LAYER 1: DATA INGESTION
I started with building the local and git clone logic. This was simple enough but I wanted to make sure the mechanism for loading source code was scalable in the future. I went with a loader interface so we can load source code from different sources (GitHub or Local for now), but in future we can extend to other sources.

I first built a git parser that uses git cli to download the file
However I opted for using http to fetch a tarball straight from github.
This has 2 benefits for scalability:
1. we don't need git as a dependency
2. we can stream the response straight from github, so no need to save the source code anywhere
Trade-offs versus an actual `git clone`:
    - Public repos only (no ambient SSH/git-credential reuse).
    - No incremental refresh — every load() re-downloads the full
      tarball from scratch.
    - Always the repo's default branch (HEAD) — no ref/branch selection.

in future, we will need to save the downloaded code somewhere, as likely we will not process it as part of the same compute instance.

# LAYER 2: FILTERING
Parsing, chunking and embedding all files would be wasteful. As such it makes sense to filter out files that are not useful: common dependency/build directories (`.git`, `node_modules`, `dist`, `.venv` etc.), as well as anything over 500KB to remove binary files.

What's left maps to a language by file extension. Files with an unrecognised extension fall through as plain `"text"` instead (since chunking layer has a sliding-window fallback for files with non AST grammar). e.g. README or Dockerfile has no AST but is still worth indexing.

# LAYER 3: PARSING
I wanted to be able to chunk source code intelligently, not just using classic token based chunking with overlap, but instead intelligent chunking on logical boundaries (functions, classes, etc.)

## Abstract Syntax Tree (AST)
I decided that the best solution for this is to introduce the dependency of tree-sitter. This can dynamically handle the parsing of source code files from different languages. I built the language definition system that can be easily extendable in future (add a `.scm` file, and make a `LanguageConfig` in the `registry.py`). For now I only built definitions for a few common languages.

Tree-splitter was a package that I was not familiar with. I asked AI to implement a few common programming languages. The code seemed to balloon in complexity beyond my understanding. If I had more time I would try to understand in further detail. But instead for now I asked the AI to make detailed implementation notes that I could read later or could later be picked up by another Agent in the future.

I decided to store the parsed symbols as the raw unmodified text (instead of decorating with a heading with metadata). This allows us maximum flexibility on how to implement it later, as well as allowing the next layer (which knows what embedding model is being used), to decide the best strategy to decorate the chunks.

# LAYER 4: CHUNKING
Different embedding models have different token limits and different retrieval-quality sweet spots. When the application is built, we will need to test and optimise this. To facilitate this we expose a `ChunkConfig`, defining `split_threshold`, `window_size`, `window_overlap` & `gap_min_size`.

I decided not to implement a tokenizer, for the speed of this task, but also because different embedding model could tokenize in differently, so it would not be accurate at this stage.
Instead we use the ~4 tokens per char approximation. at a later stage it may be worth implementing an interface to inject a tokenizer into this stage, but it is out of the scope of this task.

For symbols that exceed the max token count, I decided to use a traditional token based chunking with overlap %, so a concept that straddles a cut point still shows up whole in at least one piece.

## Non Symbol Code
The AST parser only sees symbols like functions and classes, it ignores all other code, for example, imports, global constants or docstrings. There is still valuable logic in that information. I decided to fill that gap by chunking whatever is left over using the same sliding window approach.

I chose to use this same mechanism for non code files, such as README, yaml or Dockerfile. A README for example, can often be the single most useful file in a repository.

I decided to skip files with no value for semantic search, such as binary or extremely large files.

# LAYER 5: EMBEDDING

## Embedding modal
I considered to use a few differnt lightweight embedding models for this task
`jina-embeddings-v2-base-code` - Code-specific training, strong semantic fit
`nomic-embed-text` - Fast, well-maintained, available to serve viaa Ollama 
`all-MiniLM-L6-v2` - Weakest quality, not code-aware
`microsoft/codebert-base` - Real code-pretrained transformer but needs manual pooling
I decided to use `nomic-embed-text` served via Ollama daemon - It seemed like a decent place to start, and its the easiest to set up on my machine. The code-specific models are the obvious upgrade path once retrieval quality actually gets measured rather than eyeballed.

Ollama as a daemon over an in-process model (e.g. sentence-transformers), decouples the model from this process so swapping models later doesn't touch code, at the cost of an extra moving part that has to be running.

Chunks are stored raw and get a header (`file_path :: symbol_kind qualified_name`) added right before embedding.
This keeps "how to represent a chunk to the model" a decision local to this layer, swappable per embedding model without touching storage parsing or chunking.

Vector dimension (768) is pinned to this model and baked into the storage at this point.


# LAYER 6: STORAGE

I chose to go with SQLite + `sqlite-vec` over an embedded vector DB (Chroma/LanceDB) or numpy cosine in plain SQLite. Because its a real SQL-native KNN in a single file, closer to an actual production vector DB without the heavy dependency.

Two tables joined by `key`: a normal `chunks` table (indexable metadata) plus a thin `vec_chunks` table (`key` + `embedding`).
I considered folding metadata into `vec0`'s auxiliary columns instead, but that loses normal SQL indexing on it.

One SQLite file per repo, not one shared DB with a `repo_id` - simpler. I would revisit if cross-repo search became a  requirement.

Ingestion wipes and reinserts on every run rather than diffing (the loader re-downloads the full tarball each time). Theres no incremental reprocessing anywhere else yet either, so seemed pointless to implement at this stage.

Vector column dimension is fixed at table creation for now (768, `nomic-embed-text`).
A future model/dimension change needs a new table or migration, its a trade-off I made for time and simplicity.

Blocker hit mid-build: `sqlite-vec` needs SQLite extension-loading support,
which my machine's does not support. I found instead `apsw` which bundles its own SQLite with extension loading enabled - would like to remove this dep in future.

# LAYER 7: TOOLS
`search_code`/`read_file`/`list_files` — the same three functions the MCP server exposes, backed by the finished Loader/Parsing/Filtering/Chunking/Embedding/Storage pipeline instead of a mock. One implementation, reused by both the MCP server (see Interface, above) and the agent loop (layer 8) — Anthropic tool schemas in `backend/src/api/agent/tools.py` just wrap the same `dispatch()` the MCP server calls. `find_symbol`/`find_callers` were considered and deliberately deferred — `find_symbol` was cheaply available (the `chunks` table already carries `qualified_name`/`symbol_kind`), `find_callers` genuinely wasn't (no `Symbol` field anywhere captures call-expressions yet) — kept to exactly `context.md`'s original three tools rather than build one and not the other. See [plans/07-tools.md](plans/07-tools.md).

# LAYER 8: AGENT LOOP
A manual `tool_use` -> execute -> `tool_result` -> repeat loop against the raw Anthropic `/v1/messages` API (`backend/src/api/agent/`), capped at 5 tool-call rounds per question — matches `context.md`'s original "raw API + manual loop, not the Agent SDK" decision. `ask()` also accumulates every `search_code` result it sees along the way (not `read_file`/`list_files`) into an `AgentResult.citations` list, added this session specifically so the HTTP layer (9) and frontend (10) could show what actually grounded an answer, not just the answer text.

# LAYER 9: HTTP API
A thin FastAPI wrapper (`backend/src/api/server/main.py`) over the two things a caller does with a repo — ingest it, then ask it questions — plus a third: list what's already been ingested. Three decisions made this session, each walked with the user rather than assumed:

- **`/ingest` streams progress as newline-delimited JSON** instead of one blocking response. Every layer underneath (`Loader`, `chunking.run()`, `embedding.run()`) was already a generator producing these numbers as it went — `ingest_repo()` was the only place collapsing them into `list()` calls before this. Embedding gets a real fraction (`chunks_embedded`/`chunks_total`, since the total is known once chunking finishes); loading/chunking get a running counter (no total available until they're already done). A direct consequence: by the time ingestion can fail, the response has already started streaming (status 200 already sent), so a `LoadError`/`EmbedError`/`StoreError` surfaces as a terminal `{"phase": "error", ...}` event instead of an HTTP status. See [plans/10-ingest-progress.md](plans/10-ingest-progress.md).
- **`/ask` returns the `search_code` citations behind its answer**, not just the answer text — pulled from the agent loop's now-accumulated results (layer 8, above) rather than a new retrieval call, so the citations are exactly what the agent actually used. `read_file`/`list_files` results are excluded — they're the agent pulling more context around something `search_code` already found, and including full file contents on every answer would balloon the payload. See [plans/08-frontend.md](plans/08-frontend.md).
- **`GET /repos` lists every already-ingested repo.** Needed a real fix to get there: each repo's `.db` filename is `<slugified-repo-source>-<sha256[:8]>.db` — lossy and irreversible, so a directory listing alone can't recover the real `repo_source` a caller would need. Fixed by writing a small `meta` table (`repo_source`, `chunks_ingested`, `ingested_at`) into each `.db` at ingest time, self-contained rather than a separate manifest file that could drift out of sync. Also found and fixed a real pre-existing bug while building this: the storage layer's `DEFAULT_ROOT` path math was off by one directory level since an earlier `src/rag/` reorg, silently writing indexes to `src/data/store` instead of the intended `<repo-root>/data/store`. See [plans/09-repo-list.md](plans/09-repo-list.md).

# LAYER 10: FRONTEND
A React + TypeScript + Tailwind v4 single-page app (`frontend/`, Vite-scaffolded), built this session as the "lightweight web-app chatbot-like frontend" option the Interface section considered and deferred. Kept deliberately small: no component library (raw Tailwind utility classes), no client state library (plain `useState` + native `fetch` — two POST calls and a handful of state slices don't need React Query), a single fixed dark theme with no light-mode toggle. `react-markdown` + `rehype-highlight` render the chat answer and the preview pane's source chunks, tagging each chunk's code fence with a language inferred from its file extension — an untagged fence renders as plain uncolored text regardless of content, which was a real early bug, not just a missing feature.

Three panes: an ingest form + live-updating list of indexed repos on the left, chat in the middle, a preview pane on the right showing the `search_code` citations behind the current answer. Ingest status is tracked per repo (`Record<repo_source, IngestStatus>`), not in one global slot — an early version used one slot and had a real bug where starting to ingest one repo, then switching to another before it finished, silently lost the first repo's progress (and its still-running background updates kept overwriting the second repo's status). See [plans/10-ingest-progress.md](plans/10-ingest-progress.md) decision #3 for how that was found and fixed, with a regression test that reproduces the exact sequence.

See [plans/08-frontend.md](plans/08-frontend.md) for the full set of scaffolding decisions.

# FUTURE IMPROVEMENTS:
- benchmark embedding models (`nomic-embed-text` vs `jina-embeddings-v2-base-code` etc.) and chunking configs (`window_size`/`window_overlap`/`split_threshold`) against a real retrieval-quality metric
- pre-filter candidates (e.g. by language, file path/extension, symbol type) before running semantic search. This narrows the vector search space and should improve retrieval accuracy.
- Add a separate graph store alongside the vector store, capturing structural relationships between symbols. Vector search can't answer structural questions like "what calls this function". A graph store would allow us to build tools like `find_callers`.
- containerise (Dockerfile + compose, including Ollama)
- instead of clean wipe and re-ingestion each time, implement diff based re-embedding for repo changes
- Ingest progress: implement current-file-name visibility in loading/chunking events
- a delete/remove-repo action in the frontend's repo list — list-and-select only today
- Perhaps filter out unit-test files - or have a flag to allow user to specify this. Test files may not always be useful.


# SCALING TO CLOUD
This is the payoff of the micro-services design choice set out at the start of the project.
Layers were deliberately built to have no cross dependancy (aside from some dataclasses which can be generalised later with ease):

Every layer is already isolated enough to lift out unmodified: put it in its own Dockerfile, and it runs as an independent container or function. 

Each layer can be containerised, scaled, redeployed, and versioned on its own schedule.
That's exactly what's needed once a layer like embedding (bound by an embedding-model TPM quota) has to sit behind a managed queue while the cheap
layers ahead of it (loading, parsing, chunking) run unthrottled on independent compute.

**Ingestion** - event-driven (webhook/EventBridge on repo push) instead of one
blocking script; embedding moves behind a queue (SQS) to absorb the TPM-quota
problem, scaling independently of the cheap steps ahead of it.

**Storage** - one SQLite file per repo is the first thing that stops scaling.
Swap `sqlite-vec` for a managed vector store (pgvector/OpenSearch) for
concurrent multi-repo access.

**Models** - swap the local Ollama daemon for a hosted embedding model (e.g.
Cohere) to scale embedding throughput. The reasoning/answering layer should be built with AWS Bedrock / AgentCore directly instead of using claudes API.

**Serving** - backend behind API Gateway + Lambda, frontend served via Cloudfront

**Guardrails** - ingest-time filtering, grounded/cited answers only, retrieved repo content treated as untrusted data not instructions (prompt-injection risk), and rate/cost caps on the reasoning API.

**Multi-tenancy** - `repo_source` is a baked-in CLI arg today; production needs
it as a per-request parameter with real tenant isolation, not a file per repo.