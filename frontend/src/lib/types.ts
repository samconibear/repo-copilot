export interface Citation {
  file_path: string;
  start_line: number;
  end_line: number;
  qualified_name: string | null;
  score: number | string;
  content: string;
}

export interface RepoInfo {
  repo_source: string;
  chunks_ingested: number;
  ingested_at: string;
}

export interface AskResponse {
  repo_source: string;
  answer: string;
  citations: Citation[];
}

export type IngestEvent =
  | { phase: "loading"; files_loaded: number }
  | { phase: "chunking"; chunks_produced: number }
  | { phase: "embedding"; chunks_embedded: number; chunks_total: number }
  | { phase: "storing" }
  | { phase: "done"; chunks_ingested: number }
  | { phase: "error"; detail: string };

export type IngestStatus =
  | { state: "loading"; event: IngestEvent | null }
  | { state: "ready"; chunksIngested: number }
  | { state: "error"; message: string };

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}
