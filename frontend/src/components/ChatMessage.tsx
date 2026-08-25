import type { ComponentPropsWithoutRef } from "react";
import Markdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import { citationAwareUrlTransform, linkifyCitations, parseCitationHref } from "../lib/citationLinks";
import type { ChunkTarget } from "../lib/citationLinks";
import type { ChatMessage as ChatMessageT } from "../lib/types";

interface ChatMessageProps {
  message: ChatMessageT;
  onCitationClick: (target: ChunkTarget) => void;
}

export function ChatMessage({ message, onCitationClick }: ChatMessageProps) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] rounded-lg bg-indigo-500 px-3 py-2 text-sm text-white">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-100">
      <div className="prose-chat">
        <Markdown
          rehypePlugins={[rehypeHighlight]}
          urlTransform={citationAwareUrlTransform}
          components={{ a: (props) => <CitationLink {...props} onCitationClick={onCitationClick} /> }}
        >
          {linkifyCitations(message.content)}
        </Markdown>
      </div>
      {message.citations && message.citations.length > 0 && (
        <p className="mt-1.5 text-xs text-indigo-200/80">
          grounded in {message.citations.length} chunk
          {message.citations.length === 1 ? "" : "s"} — click a citation above to jump to it
        </p>
      )}
    </div>
  );
}

function CitationLink({
  href,
  children,
  onCitationClick,
  node: _node,
  ...rest
}: ComponentPropsWithoutRef<"a"> & { node?: unknown; onCitationClick: (target: ChunkTarget) => void }) {
  const target = href ? parseCitationHref(href) : null;
  if (!target) {
    return (
      <a {...rest} href={href} target="_blank" rel="noreferrer">
        {children}
      </a>
    );
  }
  return (
    <button
      type="button"
      onClick={() => onCitationClick(target)}
      className="rounded bg-indigo-500/10 px-1 py-0.5 font-mono text-[0.85em] text-indigo-300 hover:bg-indigo-500/20 hover:text-indigo-200"
    >
      {children}
    </button>
  );
}
