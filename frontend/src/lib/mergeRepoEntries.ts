import type { RepoListEntry } from "../components/RepoList";
import type { IngestStatus, RepoInfo } from "./types";

export function mergeRepoEntries(
  repos: RepoInfo[],
  repoStatus: Record<string, IngestStatus>,
): RepoListEntry[] {
  const bySource = new Map<string, RepoListEntry>();
  for (const r of repos) {
    bySource.set(r.repo_source, {
      repo_source: r.repo_source,
      status: { state: "ready", chunksIngested: r.chunks_ingested },
      ingestedAt: r.ingested_at,
    });
  }
  for (const [source, status] of Object.entries(repoStatus)) {
    bySource.set(source, { ...bySource.get(source), repo_source: source, status });
  }
  return [...bySource.values()].sort((a, b) => {
    const aLoading = a.status.state === "loading" ? 1 : 0;
    const bLoading = b.status.state === "loading" ? 1 : 0;
    if (aLoading !== bLoading) return bLoading - aLoading;
    return (b.ingestedAt ?? "").localeCompare(a.ingestedAt ?? "");
  });
}
