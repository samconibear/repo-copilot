export const PREVIEW_LINES = 6;

export interface ChunkPreview {
  displayContent: string;
  totalLines: number;
  isTruncatable: boolean;
}

export function previewChunk(content: string, maxLines: number = PREVIEW_LINES): ChunkPreview {
  const lines = content.split("\n");
  const isTruncatable = lines.length > maxLines;
  return {
    displayContent: isTruncatable ? lines.slice(0, maxLines).join("\n") : content,
    totalLines: lines.length,
    isTruncatable,
  };
}
