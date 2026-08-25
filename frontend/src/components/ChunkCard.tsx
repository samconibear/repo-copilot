import Markdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import { previewChunk } from "../lib/chunkPreview";
import { languageForPath } from "../lib/language";
import { computeLineOverlay } from "../lib/lineOverlay";
import type { Citation } from "../lib/types";

function asCodeBlock(content: string, filePath: string): string {
  const lang = languageForPath(filePath) ?? "";
  return "```" + lang + "\n" + content.trimEnd() + "\n```";
}

interface ChunkCardProps {
  chunk: Citation;
  expanded: boolean;
  highlighted: boolean;
  highlightLines: { startLine: number; endLine: number } | null;
  onToggleExpanded: () => void;
  cardRef: (el: HTMLDivElement | null) => void;
}

const LINE_HEIGHT_REM = 1;

export function ChunkCard({
  chunk,
  expanded,
  highlighted,
  highlightLines,
  onToggleExpanded,
  cardRef,
}: ChunkCardProps) {
  const loc = `${chunk.file_path}:${chunk.start_line}-${chunk.end_line}`;

  const { displayContent, totalLines, isTruncatable } = previewChunk(chunk.content);
  const content = expanded ? chunk.content : displayContent;
  const displayedLineCount = content.split("\n").length;

  const overlay = highlightLines
    ? computeLineOverlay(
        chunk.start_line,
        displayedLineCount,
        highlightLines.startLine,
        highlightLines.endLine,
      )
    : null;

  return (
    <div
      ref={cardRef}
      className={`rounded-md border bg-zinc-900 transition-shadow duration-300 ${
        highlighted
          ? "border-indigo-400 ring-2 ring-indigo-400 ring-offset-2 ring-offset-zinc-950"
          : "border-zinc-800"
      }`}
    >
      <div className="flex items-center justify-between gap-2 border-b border-zinc-800 px-3 py-1.5">
        <div className="min-w-0">
          <div className="truncate font-mono text-xs text-zinc-300">{loc}</div>
          {chunk.qualified_name && (
            <div className="truncate text-xs text-zinc-500">{chunk.qualified_name}</div>
          )}
        </div>
        <span className="shrink-0 rounded bg-indigo-500/10 px-1.5 py-0.5 text-xs text-indigo-300">
          {typeof chunk.score === "number" ? chunk.score.toFixed(3) : chunk.score}
        </span>
      </div>
      <div
        className={`relative px-3 py-2 text-xs ${
          overlay
            ? "overflow-x-auto [&_pre]:whitespace-pre [&_pre]:break-normal"
            : "[&_pre]:whitespace-pre-wrap [&_pre]:break-words"
        }`}
      >
        {overlay && (
          <div
            aria-hidden="true"
            data-testid="line-highlight"
            className="pointer-events-none absolute inset-x-0 rounded bg-amber-400/20"
            style={{
              top: `calc(0.5rem + ${overlay.startIndex * LINE_HEIGHT_REM}rem)`,
              height: `${overlay.lineCount * LINE_HEIGHT_REM}rem`,
            }}
          />
        )}
        <Markdown rehypePlugins={[rehypeHighlight]}>{asCodeBlock(content, chunk.file_path)}</Markdown>
      </div>
      {isTruncatable && (
        <button
          type="button"
          onClick={onToggleExpanded}
          className="flex w-full items-center justify-center gap-1 border-t border-zinc-800 py-1 text-xs text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
        >
          {expanded ? "Show less" : `Show all ${totalLines} lines`}
          <svg
            className={`h-3 w-3 transition-transform ${expanded ? "rotate-180" : ""}`}
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.168l3.71-3.938a.75.75 0 1 1 1.08 1.04l-4.25 4.5a.75.75 0 0 1-1.08 0l-4.25-4.5a.75.75 0 0 1 .02-1.06Z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      )}
    </div>
  );
}
