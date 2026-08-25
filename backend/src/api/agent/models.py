from dataclasses import dataclass, field


class AgentError(Exception):
    """Raised when the Anthropic API call fails"""


@dataclass(frozen=True)
class AgentConfig:
    model: str = "claude-sonnet-5"
    max_tokens: int = 1024
    max_iterations: int = 5  # cap tool-call rounds per turn
    base_url: str = "https://api.anthropic.com/v1/messages"
    api_version: str = "2023-06-01"


@dataclass(frozen=True)
class AgentResult:
    answer: str
    citations: list[dict] = field(default_factory=list)
