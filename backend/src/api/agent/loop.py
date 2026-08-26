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
    seen: set[tuple[object, object, object]] = set()

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
                for hit in result:
                    _add_citation(citations, seen, hit)
            elif block["name"] == "read_file" and isinstance(result, str):
                _add_citation(citations, seen, _read_file_citation(block["input"].get("path", ""), result))
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block["id"], "content": json.dumps(result)}
            )
        messages.append({"role": "user", "content": tool_results})

    return AgentResult(
        answer="(reached max tool-call iterations without a final answer)",
        citations=citations,
    )


def _read_file_citation(path: str, content: str) -> dict:
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
        "score": "Bypassed RAG - read full file",
    }


def _add_citation(
    citations: list[dict], seen: set[tuple[object, object, object]], citation: dict
) -> None:
    key = (citation.get("file_path"), citation.get("start_line"), citation.get("end_line"))
    if key in seen:
        return
    seen.add(key)
    citations.append(citation)


def _run_tool(repo_source: str, name: str, tool_input: dict) -> object:
    try:
        return dispatch(repo_source, name, tool_input)
    except Exception as e:
        return {"error": str(e)}


def _extract_text(content: list[dict]) -> str:
    return "\n".join(block["text"] for block in content if block["type"] == "text")
