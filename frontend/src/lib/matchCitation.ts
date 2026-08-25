import type { ChunkTarget } from "./citationLinks";
import type { Citation } from "./types";

export function findMatchingCitation(
  citations: Citation[],
  target: ChunkTarget,
): Citation | null {
  const exact = citations.find(
    (c) =>
      c.file_path === target.filePath &&
      c.start_line === target.startLine &&
      c.end_line === target.endLine,
  );
  if (exact) return exact;

  const overlapping = citations.find(
    (c) =>
      c.file_path === target.filePath &&
      target.startLine <= c.end_line &&
      target.endLine >= c.start_line,
  );
  return overlapping ?? null;
}
