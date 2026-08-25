import { useEffect, useRef, useState } from "react";
import type { ChunkTarget } from "../lib/citationLinks";
import { chunkKey } from "../lib/chunkKey";
import { findMatchingCitation } from "../lib/matchCitation";
import type { Citation } from "../lib/types";
import { ChunkCard } from "./ChunkCard";

interface Highlight {
  key: string;
  startLine: number;
  endLine: number;
}

interface PreviewPaneProps {
  citations: Citation[];
  focusTarget: ChunkTarget | null;
}

export function PreviewPane({ citations, focusTarget }: PreviewPaneProps) {
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(new Set());
  const [highlight, setHighlight] = useState<Highlight | null>(null);
  const nodeRefs = useRef(new Map<string, HTMLDivElement>());

  useEffect(() => {
    if (!focusTarget) return;
    const match = findMatchingCitation(citations, focusTarget);
    if (!match) return;

    const key = chunkKey(match);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setExpandedKeys((prev) => (prev.has(key) ? prev : new Set(prev).add(key)));
    setHighlight({ key, startLine: focusTarget.startLine, endLine: focusTarget.endLine });
    nodeRefs.current.get(key)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [focusTarget, citations]);

  function toggleExpanded(key: string) {
    setExpandedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  return (
    <aside className="flex min-w-0 flex-1 flex-col border-l border-zinc-800 bg-zinc-950">
      <div className="border-b border-zinc-800 px-4 py-3">
        <h2 className="text-sm font-medium text-zinc-300">Source chunks</h2>
        <p className="text-xs text-zinc-500">
          What the agent searched to answer the last question
        </p>
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto p-3">
        {citations.length === 0 ? (
          <p className="px-1 text-sm text-zinc-500">
            Ask a question to see the chunks it's grounded in.
          </p>
        ) : (
          citations.map((chunk) => {
            const key = chunkKey(chunk);
            const isHighlighted = highlight?.key === key;
            return (
              <ChunkCard
                key={key}
                chunk={chunk}
                expanded={expandedKeys.has(key)}
                highlighted={isHighlighted}
                highlightLines={
                  isHighlighted && highlight
                    ? { startLine: highlight.startLine, endLine: highlight.endLine }
                    : null
                }
                onToggleExpanded={() => toggleExpanded(key)}
                cardRef={(el) => {
                  if (el) nodeRefs.current.set(key, el);
                  else nodeRefs.current.delete(key);
                }}
              />
            );
          })
        )}
      </div>
    </aside>
  );
}
