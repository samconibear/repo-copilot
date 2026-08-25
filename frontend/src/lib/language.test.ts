import { describe, expect, it } from "vitest";
import { languageForPath } from "./language";

describe("languageForPath", () => {
  it("maps common extensions to their highlight.js language name", () => {
    expect(languageForPath("src/api/server/main.py")).toBe("python");
    expect(languageForPath("src/App.tsx")).toBe("typescript");
    expect(languageForPath("engine.rs")).toBe("rust");
  });

  it("is case-insensitive on the extension", () => {
    expect(languageForPath("README.MD")).toBe("markdown");
  });

  it("uses the last extension for a multi-dot filename", () => {
    expect(languageForPath("vite.config.ts")).toBe("typescript");
  });

  it("returns undefined for an extension outside the known set, not a wrong guess", () => {
    expect(languageForPath("Dockerfile")).toBeUndefined();
    expect(languageForPath("data.toml")).toBeUndefined();
  });

  it("returns undefined for a path with no extension at all", () => {
    expect(languageForPath("Makefile")).toBeUndefined();
  });
});
