import { IngestForm } from "./IngestForm";
import type { RepoListEntry } from "./RepoList";
import { RepoList } from "./RepoList";

interface SidebarProps {
  onIngest: (repoSource: string) => void;
  entries: RepoListEntry[];
  reposLoading: boolean;
  activeRepoSource: string | null;
  onSelectRepo: (repoSource: string) => void;
}

export function Sidebar({
  onIngest,
  entries,
  reposLoading,
  activeRepoSource,
  onSelectRepo,
}: SidebarProps) {
  return (
    <aside className="flex w-72 shrink-0 flex-col border-r border-zinc-800 bg-zinc-950">
      <IngestForm onIngest={onIngest} />
      <RepoList
        entries={entries}
        activeRepoSource={activeRepoSource}
        loading={reposLoading}
        onSelect={onSelectRepo}
      />
    </aside>
  );
}
