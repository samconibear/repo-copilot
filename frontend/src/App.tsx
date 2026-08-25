import { useEffect, useState } from "react";
import * as api from "./lib/api";
import type { ChunkTarget } from "./lib/citationLinks";
import { ChatPane } from "./components/ChatPane";
import { PreviewPane } from "./components/PreviewPane";
import { Sidebar } from "./components/Sidebar";
import { mergeRepoEntries } from "./lib/mergeRepoEntries";
import type { ChatMessage, Citation, IngestStatus, RepoInfo } from "./lib/types";

export default function App() {
  const [repoSource, setRepoSource] = useState<string | null>(null);
  const [focusTarget, setFocusTarget] = useState<ChunkTarget | null>(null);
  const [repoStatus, setRepoStatus] = useState<Record<string, IngestStatus>>({});
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [pending, setPending] = useState(false);
  const [repos, setRepos] = useState<RepoInfo[]>([]);
  const [reposLoading, setReposLoading] = useState(true);

  function setStatusFor(source: string, status: IngestStatus) {
    setRepoStatus((prev) => ({ ...prev, [source]: status }));
  }

  async function refreshRepos() {
    try {
      setRepos(await api.listRepos());
    } catch (e) {
      void e;
    } finally {
      setReposLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refreshRepos();
  }, []);

  async function handleIngest(source: string) {
    setRepoSource(source);
    setMessages([]);
    setCitations([]);
    setStatusFor(source, { state: "loading", event: null });
    try {
      let chunksIngested: number | null = null;
      let errorDetail: string | null = null;
      await api.ingestStream(source, (event) => {
        if (event.phase === "done") {
          chunksIngested = event.chunks_ingested;
          return;
        }
        if (event.phase === "error") {
          errorDetail = event.detail;
          return;
        }
        setStatusFor(source, { state: "loading", event });
      });
      if (errorDetail !== null) {
        setStatusFor(source, { state: "error", message: errorDetail });
      } else if (chunksIngested !== null) {
        setStatusFor(source, { state: "ready", chunksIngested });
        refreshRepos();
      }
    } catch (e) {
      setStatusFor(source, {
        state: "error",
        message: e instanceof Error ? e.message : "ingest failed",
      });
    }
  }

  function handleSelectRepo(source: string) {
    if (source === repoSource) return;
    setRepoSource(source);
    setMessages([]);
    setCitations([]);
    setRepoStatus((prev) => {
      if (prev[source]) return prev;
      const known = repos.find((r) => r.repo_source === source);
      if (!known) return prev;
      return { ...prev, [source]: { state: "ready", chunksIngested: known.chunks_ingested } };
    });
  }

  async function handleAsk(question: string) {
    if (!repoSource) return;
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setPending(true);
    try {
      const res = await api.ask(repoSource, question);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.answer, citations: res.citations },
      ]);
      setCitations(res.citations);
    } catch (e) {
      const message = e instanceof Error ? e.message : "ask failed";
      setMessages((prev) => [...prev, { role: "assistant", content: `⚠️ ${message}` }]);
    } finally {
      setPending(false);
    }
  }

  const repoEntries = mergeRepoEntries(repos, repoStatus);

  const activeStatus = repoSource ? repoStatus[repoSource] : undefined;
  const ready = activeStatus?.state === "ready";
  const disabledReason =
    activeStatus?.state === "loading"
      ? "waiting for ingestion to finish…"
      : activeStatus?.state === "error"
        ? "last ingest failed — try again"
        : "ingest or select a repo on the left first";

  return (
    <div className="flex h-screen flex-col bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 px-4 py-3">
        <h1 className="text-base font-semibold text-zinc-100">Repo Copilot</h1>
      </header>
      <div className="flex min-h-0 flex-1">
        <Sidebar
          onIngest={handleIngest}
          entries={repoEntries}
          reposLoading={reposLoading}
          activeRepoSource={repoSource}
          onSelectRepo={handleSelectRepo}
        />
        <ChatPane
          messages={messages}
          disabled={!ready}
          disabledReason={disabledReason}
          pending={pending}
          onAsk={handleAsk}
          onCitationClick={setFocusTarget}
        />
        <PreviewPane citations={citations} focusTarget={focusTarget} />
      </div>
    </div>
  );
}
