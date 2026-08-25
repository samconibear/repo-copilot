export interface LineOverlay {
  startIndex: number;
  lineCount: number;
}

export function computeLineOverlay(
  chunkStartLine: number,
  displayedLineCount: number,
  highlightStartLine: number,
  highlightEndLine: number,
): LineOverlay | null {
  const startIndex = Math.max(0, highlightStartLine - chunkStartLine);
  const endIndex = Math.min(displayedLineCount - 1, highlightEndLine - chunkStartLine);
  if (startIndex > endIndex) return null;
  return { startIndex, lineCount: endIndex - startIndex + 1 };
}
