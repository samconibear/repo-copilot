# Application Architecture

Repo-Copilot has two flows sharing one storage layer:
**ingestion** (build the index for a repo)
**serving** (answer questions against an ingested repo, via HTTP API, MCP server, or the frontend).

See the README for the full layer-by-layer design rationale.

## Ingestion pipeline (Layers 1–6)

```mermaid
flowchart LR
    Source(["GitHub URL / local path"]) --> Loader

    subgraph Pipeline["backend/src/rag"]
        Loader["1. Loader\n(git tarball / local)"]
        Filter["2. Filtering\n(skip build dirs, binaries,\nlanguage detection)"]
        Parse["3. Parsing\n(tree-sitter AST\nsymbols)"]
        Chunk["4. Chunking\n(split oversized symbols,\nsliding window for the rest)"]
        Embed["5. Embedding\n(Ollama: nomic-embed-text)"]
        Store[("6. Storage\nSQLite + sqlite-vec\none .db per repo")]

        Loader --> Filter --> Parse --> Chunk --> Embed --> Store
    end

    Ollama[("Ollama daemon\n(local)")] -. embeds via .-> Embed
```

## Serving path (Layers 7–10)

```mermaid
flowchart LR
    subgraph Clients
        FE["10. Frontend\nReact + Tailwind (Vite)"]
        MCPClient["MCP client\n(Claude Code / Claude Desktop)"]
    end

    subgraph Backend["backend/src/api"]
        HTTP["9. HTTP API\nFastAPI (server/main.py)\nPOST /ingest, /ask, GET /repos"]
        MCPServer["MCP server (stdio)\nsearch_code / read_file / list_files"]
        Agent["8. Agent loop\nAnthropic /v1/messages\ntool_use -> execute -> tool_result\n(max 5 rounds)"]
        Tools["7. Tools\nsearch_code / read_file / list_files\n(dispatch())"]
    end

    Store[("SQLite + sqlite-vec\n(per-repo .db)")]
    Claude[["Anthropic API\n(Claude)"]]

    FE -- "HTTP" --> HTTP
    MCPClient -- "MCP / stdio" --> MCPServer

    HTTP --> Agent
    MCPServer --> Tools
    Agent --> Tools
    Agent -- "tool_use / tool_result" --> Claude

    Tools --> Store
    HTTP -- "/ingest" --> IngestPipeline["Ingestion pipeline\n(Layers 1-6)"]
```

## End-to-End Architecture

```mermaid
flowchart TB
    User(["USER"])

    subgraph Clients["Clients"]
        FE["10. Frontend\nReact + Tailwind (Vite)\nport 5173"]
        MCPClient["MCP client\n(Claude Code / Claude Desktop)"]
        CLI["scripts.ingest / scripts.demo\n(CLI, backend/)"]
    end

    User --> FE
    User --> MCPClient
    User --> CLI

    subgraph Backend["Backend (FastAPI + MCP server, backend/src/api)"]
        HTTP["9. HTTP API\nserver/main.py\nPOST /ingest, /ask, GET /repos\nport 8000"]
        MCPServer["MCP server (stdio)\nmcp/server.py"]
        Agent["8. Agent loop\nagent/loop.py\ntool_use -> execute -> tool_result\n(max 5 rounds)"]
        Tools["7. Tools\nsearch_code / read_file / list_files\ndispatch()"]
    end

    FE -- HTTP --> HTTP
    MCPClient -- "MCP / stdio" --> MCPServer
    CLI --> Pipeline

    HTTP -- "/ask" --> Agent
    HTTP -- "/ingest" --> Pipeline
    MCPServer --> Tools
    Agent --> Tools
    Agent -- "tool_use / tool_result" --> Claude[["Anthropic API\n(Claude)"]]

    subgraph Pipeline["Ingestion pipeline (backend/src/rag, Layers 1-6)"]
        direction LR
        Loader["1. Loader\ngit tarball / local"]
        Filter["2. Filtering\nlanguage detection"]
        Parse["3. Parsing\ntree-sitter AST"]
        Chunk["4. Chunking\nsliding window"]
        Embed["5. Embedding"]
        Loader --> Filter --> Parse --> Chunk --> Embed
    end

    Ollama[("Ollama daemon\nnomic-embed-text\nlocal")]
    Embed -. embeds via .-> Ollama
    Embed --> Store

    Store[("6. Storage\nSQLite + sqlite-vec\none .db per repo\nbackend/data/store")]
    Tools --> Store

    GitHub[("GitHub\n(tarball fetch)")]
    Local[("Local filesystem\n(repo path)")]
    Loader -.-> GitHub
    Loader -.-> Local
```

## Notes

- The two flows share the same storage layer.
- `Tools` (Layer 7) is a single implementation reused by both the MCP server and the agent loop.
- Requires a locally running Ollama daemon (`nomic-embed-text`) for embedding, and an `ANTHROPIC_API_KEY` for the reasoning layer and agent loop's calls to Claude.
