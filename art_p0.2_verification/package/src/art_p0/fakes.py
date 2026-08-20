from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class FakeAssistantMessage:
    content: str | None = None
    tool_calls: list[FakeToolCall] = field(default_factory=list)


@dataclass
class FakeHarness:
    harness_id: str
    prompt: str
    policy: dict[str, Any]
