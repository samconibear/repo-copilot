import { type FormEvent, useEffect, useRef, useState } from "react";
import type { ChunkTarget } from "../lib/citationLinks";
import type { ChatMessage as ChatMessageT } from "../lib/types";
import { ChatMessage } from "./ChatMessage";

interface ChatPaneProps {
  messages: ChatMessageT[];
  disabled: boolean;
  disabledReason: string;
  pending: boolean;
  onAsk: (question: string) => void;
  onCitationClick: (target: ChunkTarget) => void;
}

export function ChatPane({
  messages,
  disabled,
  disabledReason,
  pending,
  onAsk,
  onCitationClick,
}: ChatPaneProps) {
  const [question, setQuestion] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pending]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = question.trim();
    if (trimmed && !disabled && !pending) {
      onAsk(trimmed);
      setQuestion("");
    }
  }

  return (
    <main className="flex min-w-0 flex-1 flex-col">
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && (
          <p className="text-sm text-zinc-500">
            {disabled ? disabledReason : "Ask something about the ingested repo."}
          </p>
        )}
        {messages.map((m, i) => (
          <ChatMessage key={i} message={m} onCitationClick={onCitationClick} />
        ))}
        {pending && (
          <div className="flex justify-start">
            <div className="rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-500">
              thinking…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <form onSubmit={handleSubmit} className="flex gap-2 border-t border-zinc-800 p-3">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={disabled ? disabledReason : "Ask a question about this repo…"}
          disabled={disabled || pending}
          className="flex-1 rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 outline-none focus:border-indigo-400 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={disabled || pending || !question.trim()}
          className="rounded-md bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Ask
        </button>
      </form>
    </main>
  );
}
