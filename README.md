# Repo-Copilot
This repo exposes a codebase as an MCP server: point it at a repo (a GitHub URL or a local path) and it serves three tools — `search_code`, `read_file`,
`list_files` - over MCP. The server itself never ingests - build the index
first with `scripts.ingest` (see below), then point the server at the same repo.

## Prerequisites

- **Python 3.14.6** ([.python-version](.python-version)). If you use `pyenv`:
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

## Install

```bash
python3.14 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Ingest a repo

The server only reads an existing index - it never ingests itself. Build (or
rebuild) one first with the standalone ingestion script:

```bash
python -m scripts.ingest <github-url-or-local-path>
# e.g.
python -m scripts.ingest https://github.com/owner/repo
python -m scripts.ingest ./path/to/local/repo
```

Every run wipes and re-ingests that repo's index from scratch - there's no
incremental/cached ingestion yet, so expect the same wait every time. Re-run
this whenever the repo changes; the server picks up the rebuilt index on its
next tool call, no restart needed.

## Run it standalone

Once a repo has been ingested, point the server at the same repo:

```bash
python -m src.mcp.server <github-url-or-local-path>
# e.g.
python -m src.mcp.server https://github.com/owner/repo
python -m src.mcp.server ./path/to/local/repo
```

## Connect an MCP client
The server speaks MCP over **stdio**. For Claude Code, add it as a project
or user MCP server:

```bash
claude mcp add repo-copilot -- python -m src.mcp.server <github-url-or-local-path>
```
(run from this repo's root, with `.venv` activated, or use the venv's
absolute Python path, e.g. `/path/to/codebase-copilot/.venv/bin/python`).

For Claude Desktop, add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "repo-copilot": {
      "command": "/absolute/path/to/codebase-copilot/.venv/bin/python",
      "args": ["-m", "src.mcp.server", "<github-url-or-local-path>"],
      "cwd": "/absolute/path/to/codebase-copilot"
    }
  }
}
```

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
|2      | Parse each file into AST symbols |
|3      | Chunk oversized symbols and non code files |
|4      | Embedding - generate vectors from code symbols |
|5      | Storage of vectors and metadata |
|6      | Interface - how we interact with the application |


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

# LAYER 2: PARSING
I wanted to be able to chunk source code intelligently, not just using classic token based chunking with overlap, but instead intelligent chunking on logical boundaries (functions, classes, etc.)

## Abstract Syntax Tree (AST)
I decided that the best solution for this is to introduce the dependency of tree-sitter. This can dynamically handle the parsing of source code files from different languages. I built the language definition system that can be easily extendable in future (add a `.scm` file, and make a `LanguageConfig` in the `registry.py`). For now I only built definitions for a few common languages.

Tree-splitter was a package that I was not familiar with. I asked AI to implement a few common programming languages. The code seemed to balloon in complexity beyond my understanding. If I had more time I would try to understand in further detail. But instead for now I asked the AI to make detailed implementation notes that I could read later or could later be picked up by another Agent in the future.

I decided to store the parsed symbols as the raw unmodified text (instead of decorating with a heading with metadata). This allows us maximum flexibility on how to implement it later, as well as allowing the next layer (which knows what embedding model is being used), to decide the best strategy to decorate the chunks.

# LAYER 3: CHUNKING
Different embedding models have different token limits and different retrieval-quality sweet spots. When the application is built, we will need to test and optimise this. To facilitate this we expose a `ChunkConfig`, defining `split_threshold`, `window_size`, `window_overlap` & `gap_min_size`.

I decided not to implement a tokenizer, for the speed of this task, but also because different embedding model could tokenize in differently, so it would not be accurate at this stage.
Instead we use the ~4 tokens per char approximation. at a later stage it may be worth implementing an interface to inject a tokenizer into this stage, but it is out of the scope of this task.

For symbols that exceed the max token count, I decided to use a traditional token based chunking with overlap %, so a concept that straddles a cut point still shows up whole in at least one piece.

## Non Symbol Code
The AST parser only sees symbols like functions and classes, it ignores all other code, for example, imports, global constants or docstrings. There is still valuable logic in that information. I decided to fill that gap by chunking whatever is left over using the same sliding window approach.

I chose to use this same mechanism for non code files, such as README, yaml or Dockerfile. A README for example, can often be the single most useful file in a repository.

I decided to skip files with no value for semantic search, such as binary or extremely large files.

# EMBEDDING

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


# STORAGE

I chose to go with SQLite + `sqlite-vec` over an embedded vector DB (Chroma/LanceDB) or numpy cosine in plain SQLite. Because its a real SQL-native KNN in a single file, closer to an actual production vector DB without the heavy dependency.

Two tables joined by `key`: a normal `chunks` table (indexable metadata) plus a thin `vec_chunks` table (`key` + `embedding`).
I considered folding metadata into `vec0`'s auxiliary columns instead, but that loses normal SQL indexing on it.

One SQLite file per repo, not one shared DB with a `repo_id` - simpler. I would revisit if cross-repo search became a  requirement.

Ingestion wipes and reinserts on every run rather than diffing (the loader re-downloads the full tarball each time). Theres no incremental reprocessing anywhere else yet either, so seemed pointless to implement at this stage.

Vector column dimension is fixed at table creation for now (768, `nomic-embed-text`).
A future model/dimension change needs a new table or migration, its a trade-off I made for time and simplicity.

Blocker hit mid-build: `sqlite-vec` needs SQLite extension-loading support,
which my machine's does not support. I found instead `apsw` which bundles its own SQLite with extension loading enabled - would like to remove this dep in future.

# INTERFACE
When it came to deciding a way for a user to interface with the vector store, I considered a few options:
1. Lightweight web-app chatbot-like frontend
2. Direct query though CLI
3. Expose as MCP server

I decided to use mcp server was the best option, given then time constraints of this task, and the familiarity interface (claude code / desktop or likewise)
In the future I will build a simple fastAPI server around  `tools.py` and build a frontend web interface to interact with it

# FUTURE IMPROVEMENTS:
- add a self-contained answering layer (direct LLM call over these tools) so the repo can answer a question on its own, not just via whatever MCP client connects
- build a simple web frontend (FastAPI + chat UI) around said answering layer
- automated tests per layer: This will be cheap as good layer boundaries architecture
- benchmark embedding models (`nomic-embed-text` vs `jina-embeddings-v2-base-code` etc.) and chunking configs (`window_size`/`window_overlap`/`split_threshold`) against a real retrieval-quality metric
- add filters on retrieval
- containerise (Dockerfile + compose, including Ollama)
- instead of clean wipe and re-ingestion each time, implement diff based re-embedding for repo changes

# SCALING TO CLOUD
Payoff of the layer-independence goal from the top of this doc - layers 1-5
only pass plain dataclasses, so each becomes its own deployable without a rewrite.

**Ingestion** - event-driven (webhook/EventBridge on repo push) instead of one
blocking script; embedding moves behind a queue (SQS) to absorb the TPM-quota
problem, scaling independently of the cheap steps ahead of it.

**Storage** - one SQLite file per repo is the first thing that stops scaling.
Swap `sqlite-vec` for a managed vector store (pgvector/OpenSearch) for
concurrent multi-repo access.

**Models** - swap the local Ollama daemon for a hosted embedding model (e.g.
Cohere) to scale embedding throughput; the reasoning/answering layer calls Claude's API / AWS Bedrock directly instead of local running models

**Serving** - backend behind API Gateway + Lambda, frontend served via Cloudfront

**Guardrails** - ingest-time filtering, grounded/cited answers only, retrieved repo content treated as untrusted data not instructions (prompt-injection risk), and rate/cost caps on the reasoning API.

**Multi-tenancy** - `repo_source` is a baked-in CLI arg today; production needs
it as a per-request parameter with real tenant isolation, not a file per repo.