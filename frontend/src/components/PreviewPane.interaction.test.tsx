// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Citation } from "../lib/types";
import { PreviewPane } from "./PreviewPane";

function citation(overrides: Partial<Citation> = {}): Citation {
  return {
    file_path: "src/rag/storage/engine.py",
    start_line: 90,
    end_line: 120,
    qualified_name: "search",
    score: 0.9,
    content: Array.from({ length: 31 }, (_, i) => `line ${i}`).join("\n"),
    ...overrides,
  };
}

describe("PreviewPane citation navigation - real DOM", () => {
  it("expands and highlights the chunk matching a sub-range focusTarget", () => {
    const chunk = citation();
    const { rerender } = render(<PreviewPane citations={[chunk]} focusTarget={null} />);

    expect(screen.getByText(/Show all 31 lines/)).toBeInTheDocument();

    rerender(
      <PreviewPane
        citations={[chunk]}
        focusTarget={{ filePath: "src/rag/storage/engine.py", startLine: 97, endLine: 104 }}
      />,
    );

    expect(screen.queryByText(/Show all 31 lines/)).toBeNull();
    expect(screen.getByText("Show less")).toBeInTheDocument();

    const overlay = screen.getByTestId("line-highlight");
    expect(overlay).toHaveStyle({ top: "calc(0.5rem + 7rem)", height: "8rem" });
  });

  it("does nothing when focusTarget matches no citation (wrong file)", () => {
    const chunk = citation();
    const { rerender } = render(<PreviewPane citations={[chunk]} focusTarget={null} />);

    rerender(
      <PreviewPane
        citations={[chunk]}
        focusTarget={{ filePath: "other.py", startLine: 97, endLine: 104 }}
      />,
    );

    expect(screen.getByText(/Show all 31 lines/)).toBeInTheDocument();
    expect(screen.queryByTestId("line-highlight")).toBeNull();
  });

  it("calls scrollIntoView on the matched chunk's element", () => {
    const chunk = citation();
    const scrollSpy = vi.spyOn(Element.prototype, "scrollIntoView");
    const { rerender } = render(<PreviewPane citations={[chunk]} focusTarget={null} />);

    rerender(
      <PreviewPane
        citations={[chunk]}
        focusTarget={{ filePath: "src/rag/storage/engine.py", startLine: 97, endLine: 104 }}
      />,
    );

    expect(scrollSpy).toHaveBeenCalled();
    scrollSpy.mockRestore();
  });
});
