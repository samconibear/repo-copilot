import type { Citation } from "./types";

export function chunkKey(c: Citation): string {
  return `${c.file_path}::${c.start_line}::${c.end_line}`;
}
