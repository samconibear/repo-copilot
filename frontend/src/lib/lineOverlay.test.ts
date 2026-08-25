import { describe, expect, it } from "vitest";
import { computeLineOverlay } from "./lineOverlay";

describe("computeLineOverlay", () => {
  it("maps an absolute line range to a 0-indexed offset within the chunk", () => {
    const overlay = computeLineOverlay(90, 31, 97, 104);
    expect(overlay).toEqual({ startIndex: 7, lineCount: 8 });
  });

  it("covers a single line correctly", () => {
    const overlay = computeLineOverlay(90, 31, 97, 97);
    expect(overlay).toEqual({ startIndex: 7, lineCount: 1 });
  });

  it("clips the start when the citation begins before the chunk itself", () => {
    const overlay = computeLineOverlay(90, 31, 85, 95);
    expect(overlay).toEqual({ startIndex: 0, lineCount: 6 });
  });

  it("clips the end when the citation extends past what's displayed", () => {
    const overlay = computeLineOverlay(90, 10, 95, 150);
    expect(overlay).toEqual({ startIndex: 5, lineCount: 5 });
  });

  it("returns null when the cited range is entirely before the displayed content", () => {
    expect(computeLineOverlay(90, 31, 50, 60)).toBeNull();
  });

  it("returns null when the cited range is entirely after the displayed content", () => {
    expect(computeLineOverlay(90, 10, 200, 210)).toBeNull();
  });
});
