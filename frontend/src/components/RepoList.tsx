import { embeddingFraction, phaseLabel } from "../lib/ingestProgress";
import type { IngestStatus } from "../lib/types";

export interface RepoListEntry {
  repo_source: string;
  status: IngestStatus;
  ingestedAt?: string;
}

interface RepoListProps {
  entries: RepoListEntry[];
  activeRepoSource: string | null;
  loading: boolean;
  onSelect: (repoSource: string) => void;
}

function shortLabel(repoSource: string): string {
  const trimmed = repoSource.replace(/\/$/, "").replace(/\.git$/, "");
  return trimmed.split("/").pop() || trimmed;
}

function relativeTime(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const minutes = Math.round(ms / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function RepoList({ entries, activeRepoSource, loading, onSelect }: RepoListProps) {
  return (
    <div className="flex flex-1 flex-col overflow-hidden border-t border-zinc-800">
      <div className="px-3 pt-3 pb-1">
        <h2 className="text-xs font-medium text-zinc-400">Indexed repos</h2>
      </div>
      <div className="flex-1 overflow-y-auto px-2 pb-3">
        {loading && entries.length === 0 ? (
          <p className="px-1 py-2 text-xs text-zinc-500">loading…</p>
        ) : entries.length === 0 ? (
          <p className="px-1 py-2 text-xs text-zinc-500">No repos ingested yet.</p>
        ) : (
          <ul className="space-y-1">
            {entries.map((entry) => {
              const active = entry.repo_source === activeRepoSource;
              return (
                <li key={entry.repo_source}>
                  <button
                    type="button"
                    onClick={() => onSelect(entry.repo_source)}
                    title={entry.repo_source}
                    className={`w-full rounded-md px-2 py-1.5 text-left text-sm transition-colors ${
                      active
                        ? "bg-indigo-500/15 text-indigo-200"
                        : "text-zinc-300 hover:bg-zinc-800"
                    }`}
                  >
                    <div className="truncate font-medium">{shortLabel(entry.repo_source)}</div>
                    <RepoStatusLine
                      status={entry.status}
                      ingestedAt={entry.ingestedAt}
                      active={active}
                    />
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}

function RepoStatusLine({
  status,
  ingestedAt,
  active,
}: {
  status: IngestStatus;
  ingestedAt?: string;
  active: boolean;
}) {
  const mutedColor = active ? "text-indigo-200/70" : "text-zinc-500";

  switch (status.state) {
    case "loading": {
      const fraction = status.event ? embeddingFraction(status.event) : null;
      return (
        <div className="mt-0.5">
          <div className={`truncate text-xs ${mutedColor}`}>
            {status.event ? phaseLabel(status.event) : "starting…"}
          </div>
          {fraction !== null && (
            <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-zinc-800">
              <div
                className="h-full rounded-full bg-indigo-400 transition-[width]"
                style={{ width: `${Math.round(fraction * 100)}%` }}
              />
            </div>
          )}
        </div>
      );
    }
    case "ready":
      return (
        <div className={`truncate text-xs ${mutedColor}`}>
          {status.chunksIngested} chunks
          {ingestedAt ? ` · ${relativeTime(ingestedAt)}` : ""}
        </div>
      );
    case "error":
      return <div className="truncate text-xs text-red-400">{status.message}</div>;
  }
}
