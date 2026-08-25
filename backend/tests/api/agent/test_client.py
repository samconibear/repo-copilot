import json
import urllib.error

import pytest

from src.api.agent import client
from src.api.agent.models import AgentConfig, AgentError

_CONFIG = AgentConfig(model="test-model", max_tokens=100, base_url="https://example/v1/messages")


class _FakeResponse:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_missing_api_key_raises_agent_error_without_a_network_call(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    def fail_if_called(*a, **k):
        raise AssertionError("should not reach the network without an API key")

    monkeypatch.setattr("src.api.agent.client.urllib.request.urlopen", fail_if_called)
    with pytest.raises(AgentError, match="ANTHROPIC_API_KEY"):
        client.call([], "system", [], _CONFIG)


def test_successful_call_returns_parsed_json_body(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    response_payload = {"content": [{"type": "text", "text": "hi"}], "stop_reason": "end_turn"}
    monkeypatch.setattr(
        "src.api.agent.client.urllib.request.urlopen",
        lambda request, timeout=None: _FakeResponse(response_payload),
    )
    assert client.call([], "system", [], _CONFIG) == response_payload


def test_http_error_raises_agent_error_with_status_and_body(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def raise_http_error(request, timeout=None):
        err = urllib.error.HTTPError("url", 429, "rate limited", {}, None)
        err.read = lambda: b'{"error": "rate limited"}'
        raise err

    monkeypatch.setattr("src.api.agent.client.urllib.request.urlopen", raise_http_error)
    with pytest.raises(AgentError, match="429"):
        client.call([], "system", [], _CONFIG)


def test_connection_failure_raises_agent_error(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def raise_url_error(request, timeout=None):
        raise urllib.error.URLError("timed out")

    monkeypatch.setattr("src.api.agent.client.urllib.request.urlopen", raise_url_error)
    with pytest.raises(AgentError, match="failed to reach Anthropic API"):
        client.call([], "system", [], _CONFIG)
