import { defaultUrlTransform } from "react-markdown";

const CITATION_RE = /`?\b([\w./-]+\.\w+):(\d+)-(\d+)\b`?/g;

export function linkifyCitations(markdown: string): string {
  const parts = markdown.split(/(```[\s\S]*?```)/g);
  return parts
    .map((part, i) =>
      i % 2 === 0
        ? part.replace(
            CITATION_RE,
            (_match, file: string, start: string, end: string) =>
              `[${file}:${start}-${end}](citation:${file}?start=${start}&end=${end})`,
          )
        : part,
    )
    .join("");
}

export interface ChunkTarget {
  filePath: string;
  startLine: number;
  endLine: number;
}

export function citationAwareUrlTransform(url: string): string {
  return url.startsWith("citation:") ? url : defaultUrlTransform(url);
}

export function parseCitationHref(href: string): ChunkTarget | null {
  if (!href.startsWith("citation:")) return null;
  const rest = href.slice("citation:".length);
  const queryIndex = rest.indexOf("?");
  if (queryIndex === -1) return null;
  const filePath = rest.slice(0, queryIndex);
  const params = new URLSearchParams(rest.slice(queryIndex + 1));
  const start = params.get("start");
  const end = params.get("end");
  if (!filePath || !start || !end) return null;
  return { filePath, startLine: Number(start), endLine: Number(end) };
}
