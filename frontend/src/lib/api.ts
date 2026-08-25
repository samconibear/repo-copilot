import type { AskResponse, IngestEvent, RepoInfo } from "./types";

const BASE_URL = "/api";

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init);
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new ApiError(detail?.detail ?? `${path} failed: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

async function streamNdjson<T>(response: Response, onEvent: (event: T) => void): Promise<void> {
  if (!response.body) {
    const text = await response.text();
    for (const line of text.split("\n")) {
      if (line.trim()) onEvent(JSON.parse(line) as T);
    }
    return;
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let newlineIndex = buffer.indexOf("\n");
    while (newlineIndex !== -1) {
      const line = buffer.slice(0, newlineIndex).trim();
      buffer = buffer.slice(newlineIndex + 1);
      if (line) onEvent(JSON.parse(line) as T);
      newlineIndex = buffer.indexOf("\n");
    }
  }
  const trailing = buffer.trim();
  if (trailing) onEvent(JSON.parse(trailing) as T);
}

export async function ingestStream(
  repoSource: string,
  onEvent: (event: IngestEvent) => void,
): Promise<void> {
  const res = await fetch(`${BASE_URL}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_source: repoSource }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new ApiError(detail?.detail ?? `ingest failed: ${res.status} ${res.statusText}`);
  }
  await streamNdjson<IngestEvent>(res, onEvent);
}

export function ask(repoSource: string, question: string): Promise<AskResponse> {
  return post<AskResponse>("/ask", { repo_source: repoSource, question });
}

export function listRepos(): Promise<RepoInfo[]> {
  return request<RepoInfo[]>("/repos");
}
