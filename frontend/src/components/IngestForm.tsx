import { type FormEvent, useState } from "react";

interface IngestFormProps {
  onIngest: (repoSource: string) => void;
}

export function IngestForm({ onIngest }: IngestFormProps) {
  const [repoSource, setRepoSource] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = repoSource.trim();
    if (!trimmed) return;
    onIngest(trimmed);
    setRepoSource("");
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2 p-3">
      <label htmlFor="repo-source" className="text-xs font-medium text-zinc-400">
        Ingest a repo
      </label>
      <input
        id="repo-source"
        type="text"
        value={repoSource}
        onChange={(e) => setRepoSource(e.target.value)}
        placeholder="https://github.com/owner/repo or ./local/path"
        className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-sm text-zinc-100 placeholder:text-zinc-500 text-xs outline-none focus:border-indigo-400"
      />
      <button
        type="submit"
        disabled={!repoSource.trim()}
        className="w-full rounded-md bg-indigo-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-40"
      >
        Ingest
      </button>
    </form>
  );
}
