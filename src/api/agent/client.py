import json
import os
import urllib.error
import urllib.request

from .models import AgentConfig, AgentError


def call(messages: list[dict], system: str, tools: list[dict], config: AgentConfig) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise AgentError("ANTHROPIC_API_KEY is not set")

    body = json.dumps(
        {
            "model": config.model,
            "max_tokens": config.max_tokens,
            "system": system,
            "messages": messages,
            "tools": tools,
        }
    )
    request = urllib.request.Request(
        config.base_url,
        data=body.encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": config.api_version,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise AgentError(f"Anthropic API error {e.code}: {detail}") from None
    except urllib.error.URLError as e:
        raise AgentError(f"failed to reach Anthropic API ({e.reason})") from None
