import { describe, expect, it } from "vitest";
import { findMatchingCitation } from "./matchCitation";
import type { Citation } from "./types";

function citation(overrides: Partial<Citation> = {}): Citation {
  return {
    file_path: "src/rag/storage/engine.py",
    start_line: 90,
    end_line: 120,
    qualified_name: "search",
    score: 0.9,
    content: "...",
    ...overrides,
  };
}

describe("findMatchingCitation", () => {
  it("matches on exact file/line-range equality", () => {
    const chunk = citation({ start_line: 97, end_line: 104 });
    const result = findMatchingCitation([chunk], {
      filePath: "src/rag/storage/engine.py",
      startLine: 97,
      endLine: 104,
    });
    expect(result).toBe(chunk);
  });

  it("matches when the clicked range is a sub-range of the chunk's full extent", () => {
    const chunk = citation({ start_line: 90, end_line: 120 });
    const result = findMatchingCitation([chunk], {
      filePath: "src/rag/storage/engine.py",
      startLine: 97,
      endLine: 104,
    });
    expect(result).toBe(chunk);
  });

  it("matches when the clicked range partially overlaps the chunk (not fully contained)", () => {
    const chunk = citation({ start_line: 90, end_line: 100 });
    const result = findMatchingCitation([chunk], {
      filePath: "src/rag/storage/engine.py",
      startLine: 95,
      endLine: 105,
    });
    expect(result).toBe(chunk);
  });

  it("does not match a different file even if the line range overlaps", () => {
    const chunk = citation({ file_path: "other.py", start_line: 90, end_line: 120 });
    const result = findMatchingCitation([chunk], {
      filePath: "src/rag/storage/engine.py",
      startLine: 97,
      endLine: 104,
    });
    expect(result).toBeNull();
  });

  it("does not match a genuinely disjoint line range in the same file", () => {
    const chunk = citation({ start_line: 90, end_line: 120 });
    const result = findMatchingCitation([chunk], {
      filePath: "src/rag/storage/engine.py",
      startLine: 200,
      endLine: 210,
    });
    expect(result).toBeNull();
  });

  it("returns null when citations is empty", () => {
    expect(
      findMatchingCitation([], { filePath: "x.py", startLine: 1, endLine: 2 }),
    ).toBeNull();
  });
});
