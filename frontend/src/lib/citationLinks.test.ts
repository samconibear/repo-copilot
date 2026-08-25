import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import Markdown from "react-markdown";
import { describe, expect, it } from "vitest";
import { citationAwareUrlTransform, linkifyCitations, parseCitationHref } from "./citationLinks";

describe("linkifyCitations", () => {
  it("turns a plain-text citation into a markdown link", () => {
    const out = linkifyCitations("see src/rag/storage/engine.py:97-104 for details");
    expect(out).toBe(
      "see [src/rag/storage/engine.py:97-104](citation:src/rag/storage/engine.py?start=97&end=104) for details",
    );
  });

  it("strips surrounding backticks instead of leaving them around the link", () => {
    const out = linkifyCitations("as seen in `src/foo.py:1-2`");
    expect(out).toBe("as seen in [src/foo.py:1-2](citation:src/foo.py?start=1&end=2)");
  });

  it("links every citation in a multi-claim answer, not just the first", () => {
    const out = linkifyCitations("`a.py:1-2` and also `b.py:5-9`");
    expect(out).toBe(
      "[a.py:1-2](citation:a.py?start=1&end=2) and also [b.py:5-9](citation:b.py?start=5&end=9)",
    );
  });

  it("leaves fenced code blocks untouched even if they contain a citation-shaped string", () => {
    const src = "before `x.py:1-2`\n```\nnot_a_citation.py:1-2\n```\nafter `y.py:3-4`";
    const out = linkifyCitations(src);
    expect(out).toContain("[x.py:1-2](citation:x.py?start=1&end=2)");
    expect(out).toContain("[y.py:3-4](citation:y.py?start=3&end=4)");
    expect(out).toContain("```\nnot_a_citation.py:1-2\n```");
  });

  it("does not touch text with no citation-shaped substring", () => {
    const src = "just a normal sentence about the design.";
    expect(linkifyCitations(src)).toBe(src);
  });
});

describe("parseCitationHref", () => {
  it("parses a citation href back into its parts", () => {
    expect(parseCitationHref("citation:src/foo.py?start=10&end=20")).toEqual({
      filePath: "src/foo.py",
      startLine: 10,
      endLine: 20,
    });
  });

  it("returns null for a non-citation href", () => {
    expect(parseCitationHref("https://example.com")).toBeNull();
  });

  it("returns null for a malformed citation href", () => {
    expect(parseCitationHref("citation:incomplete")).toBeNull();
  });
});

describe("citation links through the real react-markdown pipeline", () => {
  function renderAnswer(markdown: string): string {
    return renderToStaticMarkup(
      React.createElement(
        Markdown,
        { urlTransform: citationAwareUrlTransform },
        linkifyCitations(markdown),
      ),
    );
  }

  it("produces an <a> whose rendered href still parses back to the original target", () => {
    const html = renderAnswer("as implemented in `src/rag/storage/engine.py:97-104`");
    const hrefMatch = html.match(/href="([^"]*)"/);
    expect(hrefMatch).not.toBeNull();
    const target = parseCitationHref(hrefMatch![1].replace(/&amp;/g, "&"));
    expect(target).toEqual({
      filePath: "src/rag/storage/engine.py",
      startLine: 97,
      endLine: 104,
    });
  });

  it("does not produce an empty href (the actual bug: defaultUrlTransform silently stripped it)", () => {
    const html = renderAnswer("see `a.py:1-2`");
    expect(html).not.toContain('href=""');
  });
});
