import type { IngestEvent } from "./types";

export function phaseLabel(event: IngestEvent): string {
  switch (event.phase) {
    case "loading":
      return `loading files… ${event.files_loaded} so far`;
    case "chunking":
      return `chunking… ${event.chunks_produced} chunks so far`;
    case "embedding":
      return event.chunks_total > 0
        ? `embedding… ${event.chunks_embedded} / ${event.chunks_total} chunks`
        : "embedding…";
    case "storing":
      return "storing index…";
    case "done":
      return "done";
    case "error":
      return event.detail;
  }
}

export function embeddingFraction(event: IngestEvent): number | null {
  if (event.phase !== "embedding" || event.chunks_total === 0) return null;
  return event.chunks_embedded / event.chunks_total;
}
