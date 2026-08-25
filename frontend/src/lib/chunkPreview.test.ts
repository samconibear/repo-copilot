import { describe, expect, it } from "vitest";
import { previewChunk } from "./chunkPreview";

describe("previewChunk", () => {
  it("returns the full content unchanged when at or under the line limit", () => {
    const content = "a\nb\nc";
    const result = previewChunk(content, 3);
    expect(result).toEqual({ displayContent: content, totalLines: 3, isTruncatable: false });
  });

  it("truncates to the first N lines when over the limit", () => {
    const content = "a\nb\nc\nd\ne";
    const result = previewChunk(content, 3);
    expect(result.displayContent).toBe("a\nb\nc");
    expect(result.totalLines).toBe(5);
    expect(result.isTruncatable).toBe(true);
  });

  it("is not truncatable exactly at the boundary", () => {
    const content = "a\nb\nc";
    const result = previewChunk(content, 3);
    expect(result.isTruncatable).toBe(false);
  });

  it("becomes truncatable one line past the boundary", () => {
    const content = "a\nb\nc\nd";
    const result = previewChunk(content, 3);
    expect(result.isTruncatable).toBe(true);
    expect(result.displayContent).toBe("a\nb\nc");
  });

  it("uses the default preview length when none is given", () => {
    const sixLines = Array.from({ length: 6 }, (_, i) => `line ${i}`).join("\n");
    const sevenLines = sixLines + "\nline 6";
    expect(previewChunk(sixLines).isTruncatable).toBe(false);
    expect(previewChunk(sevenLines).isTruncatable).toBe(true);
  });
});
