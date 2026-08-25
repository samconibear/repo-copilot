import { describe, expect, it } from "vitest";
import { mergeRepoEntries } from "./mergeRepoEntries";
import type { IngestStatus, RepoInfo } from "./types";

describe("mergeRepoEntries", () => {
  it("shows a repo that is mid-ingest and not yet confirmed by the backend", () => {
    const repos: RepoInfo[] = [];
    const status: Record<string, IngestStatus> = {
      "./new-repo": { state: "loading", event: { phase: "loading", files_loaded: 3 } },
    };

    const entries = mergeRepoEntries(repos, status);

    expect(entries).toEqual([
      { repo_source: "./new-repo", status: status["./new-repo"], ingestedAt: undefined },
    ]);
  });

  it("prefers live status over the confirmed snapshot, but keeps the confirmed ingestedAt", () => {
    const repos: RepoInfo[] = [
      { repo_source: "./repo-a", chunks_ingested: 10, ingested_at: "2026-01-01T00:00:00Z" },
    ];
    const status: Record<string, IngestStatus> = {
      "./repo-a": { state: "loading", event: { phase: "chunking", chunks_produced: 4 } },
    };

    const [entry] = mergeRepoEntries(repos, status);

    expect(entry.status).toEqual(status["./repo-a"]);
    expect(entry.ingestedAt).toBe("2026-01-01T00:00:00Z");
  });

  it("puts in-progress repos first regardless of when confirmed repos were ingested", () => {
    const repos: RepoInfo[] = [
      { repo_source: "./old", chunks_ingested: 5, ingested_at: "2026-06-01T00:00:00Z" },
    ];
    const status: Record<string, IngestStatus> = {
      "./just-started": { state: "loading", event: null },
    };

    const entries = mergeRepoEntries(repos, status);

    expect(entries.map((e) => e.repo_source)).toEqual(["./just-started", "./old"]);
  });

  it("keeps two repos' progress fully independent when ingesting one while viewing another", () => {
    let status: Record<string, IngestStatus> = {};
    const setStatusFor = (source: string, s: IngestStatus) => {
      status = { ...status, [source]: s };
    };

    setStatusFor("./repo-a", { state: "loading", event: { phase: "loading", files_loaded: 0 } });
    setStatusFor("./repo-a", {
      state: "loading",
      event: { phase: "chunking", chunks_produced: 10 },
    });

    const repos: RepoInfo[] = [
      { repo_source: "./repo-b", chunks_ingested: 20, ingested_at: "2026-01-01T00:00:00Z" },
    ];
    setStatusFor("./repo-b", { state: "ready", chunksIngested: 20 });

    setStatusFor("./repo-a", {
      state: "loading",
      event: { phase: "embedding", chunks_embedded: 5, chunks_total: 10 },
    });

    let entries = mergeRepoEntries(repos, status);
    const a = entries.find((e) => e.repo_source === "./repo-a");
    const b = entries.find((e) => e.repo_source === "./repo-b");
    expect(a?.status).toEqual({
      state: "loading",
      event: { phase: "embedding", chunks_embedded: 5, chunks_total: 10 },
    });
    expect(b?.status).toEqual({ state: "ready", chunksIngested: 20 });

    setStatusFor("./repo-a", { state: "ready", chunksIngested: 10 });
    entries = mergeRepoEntries(repos, status);
    expect(entries.find((e) => e.repo_source === "./repo-a")?.status).toEqual({
      state: "ready",
      chunksIngested: 10,
    });
    expect(entries.find((e) => e.repo_source === "./repo-b")?.status).toEqual({
      state: "ready",
      chunksIngested: 20,
    });
  });
});
