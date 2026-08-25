// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ChatMessage } from "./ChatMessage";

function assistantMessage(content: string) {
  return { role: "assistant" as const, content };
}

describe("ChatMessage citation click - real DOM, real event", () => {
  it("clicking a rendered citation calls onCitationClick with the parsed target", () => {
    const onCitationClick = vi.fn();
    render(
      <ChatMessage
        message={assistantMessage("As implemented in `src/rag/storage/engine.py:97-104`.")}
        onCitationClick={onCitationClick}
      />,
    );

    const citation = screen.getByRole("button", { name: "src/rag/storage/engine.py:97-104" });
    fireEvent.click(citation);

    expect(onCitationClick).toHaveBeenCalledTimes(1);
    expect(onCitationClick).toHaveBeenCalledWith({
      filePath: "src/rag/storage/engine.py",
      startLine: 97,
      endLine: 104,
    });
  });

  it("clicking a second citation in the same answer resolves independently", () => {
    const onCitationClick = vi.fn();
    render(
      <ChatMessage
        message={assistantMessage("See `a.py:1-2` and also `b.py:5-9`.")}
        onCitationClick={onCitationClick}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "b.py:5-9" }));

    expect(onCitationClick).toHaveBeenCalledWith({ filePath: "b.py", startLine: 5, endLine: 9 });
  });

  it("renders plain text with no button when the answer has no citation-shaped substring", () => {
    render(
      <ChatMessage message={assistantMessage("Just a plain sentence.")} onCitationClick={vi.fn()} />,
    );
    expect(screen.queryByRole("button")).toBeNull();
  });
});
