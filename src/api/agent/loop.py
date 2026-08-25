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
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block["id"], "content": json.dumps(result)}
            )
        messages.append({"role": "user", "content": tool_results})

    return AgentResult(
        answer="(reached max tool-call iterations without a final answer)",
        citations=citations,
    )


def _run_tool(repo_source: str, name: str, tool_input: dict) -> object:
    try:
        return dispatch(repo_source, name, tool_input)
    except Exception as e:
        return {"error": str(e)}


def _extract_text(content: list[dict]) -> str:
    return "\n".join(block["text"] for block in content if block["type"] == "text")
