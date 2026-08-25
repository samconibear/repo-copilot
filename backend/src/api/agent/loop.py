"""
The agent loop: call -> tool_use -> execute tool -> tool_result -> repeat.
"""

import json

from . import client
from .models import AgentConfig, AgentResult
from .prompts import SYSTEM_PROMPT
from .tools import TOOL_SCHEMAS, dispatch

_DEFAULT_CONFIG = AgentConfig()


def ask(repo_source: str, question: str, config: AgentConfig = _DEFAULT_CONFIG) -> AgentResult:
    messages: list[dict] = [{"role": "user", "content": question}]
    citations: list[dict] = []

    for _ in range(config.max_iterations):
        response = client.call(messages, SYSTEM_PROMPT, TOOL_SCHEMAS, config)
        content = response["content"]
        messages.append({"role": "assistant", "content": content})

        if response.get("stop_reason") != "tool_use":
            return AgentResult(answer=_extract_text(content), citations=citations)

        tool_results = []
        for block in content:
            if block["type"] != "tool_use":
                continue
            result = _run_tool(repo_source, block["name"], block["input"])
            if block["name"] == "search_code" and isinstance(result, list):
                citations.extend(result)
            elif block["name"] == "read_file" and isinstance(result, str):
                citations.append(_read_file_citation(block["input"].get("path", ""), result))
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block["id"], "content": json.dumps(result)}
            )
        messages.append({"role": "user", "content": tool_results})

    return AgentResult(
        answer="(reached max tool-call iterations without a final answer)",
        citations=citations,
    )


def _read_file_citation(path: str, content: str) -> dict:
    """Turn a read_file result into a citation spanning the whole file.

    The model is told to prefer read_file for context beyond a single
    search_code chunk, and it cites lines from whatever it read - so a
    citations list built from search_code alone leaves those references
    dangling in the frontend (file present in the answer, absent from the
    source-chunk panel). This gives read_file the same shape as a
    search_code hit, covering the full line range so any sub-range the
    model cites resolves via matchCitation's overlap check.
    """
    line_count = len(content.splitlines()) or 1
    return {
        "file_path": path,
        "content": content,
        "chunk_type": "file",
        "start_line": 1,
        "end_line": line_count,
        "qualified_name": None,
        "symbol_kind": None,
        "parent": None,
        # Not a similarity score - read_file returns the file verbatim,
        # bypassing retrieval entirely, so there's no ranking to report.
        # A string here (Citation.score is float | str) instead of a
        # numeric sentinel, so the frontend can tell the two apart and
        # show this in place of a score in the badge.
        "score": "Bypassed RAG, read full file",
    }


def _run_tool(repo_source: str, name: str, tool_input: dict) -> object:
    try:
        return dispatch(repo_source, name, tool_input)
    except Exception as e:
        return {"error": str(e)}


def _extract_text(content: list[dict]) -> str:
    return "\n".join(block["text"] for block in content if block["type"] == "text")
