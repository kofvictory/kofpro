from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


class BudgetExceeded(RuntimeError):
    """Raised when an atomic batch of tool calls would exceed the hard budget."""

    def __init__(self, *, requested: int, remaining: int, used: int, limit: int):
        self.requested = requested
        self.remaining = remaining
        self.used = used
        self.limit = limit
        super().__init__(
            f"tool-call budget exceeded: requested={requested}, remaining={remaining}, "
            f"used={used}, limit={limit}"
        )


@dataclass(frozen=True)
class BudgetState:
    limit: int
    used: int = 0

    def __post_init__(self) -> None:
        if self.limit < 0:
            raise ValueError("limit must be non-negative")
        if self.used < 0 or self.used > self.limit:
            raise ValueError("used must satisfy 0 <= used <= limit")

    @property
    def remaining(self) -> int:
        return self.limit - self.used

    def can_spend(self, n: int) -> bool:
        if n < 0:
            raise ValueError("n must be non-negative")
        return n <= self.remaining

    def spend(self, n: int) -> "BudgetState":
        if n < 0:
            raise ValueError("n must be non-negative")
        if not self.can_spend(n):
            raise BudgetExceeded(
                requested=n,
                remaining=self.remaining,
                used=self.used,
                limit=self.limit,
            )
        return BudgetState(limit=self.limit, used=self.used + n)


class ToolCallBudget:
    """Hard, atomic tool-call budget.

    A message containing k tool calls is accepted iff all k fit in the remaining
    budget. The wrapper never truncates a batch because that would alter the
    underlying agent policy.
    """

    def __init__(self, limit: int):
        self._state = BudgetState(limit=limit)

    @property
    def state(self) -> BudgetState:
        return self._state

    @property
    def limit(self) -> int:
        return self._state.limit

    @property
    def used(self) -> int:
        return self._state.used

    @property
    def remaining(self) -> int:
        return self._state.remaining

    def reset(self) -> None:
        self._state = BudgetState(limit=self.limit)

    def charge(self, n: int) -> BudgetState:
        self._state = self._state.spend(n)
        return self._state

    def charge_calls(self, calls: Iterable[Any]) -> BudgetState:
        # Materialize once so generators are counted deterministically.
        batch = list(calls)
        return self.charge(len(batch))

    @staticmethod
    def count_message_tool_calls(message: Any) -> int:
        calls = getattr(message, "tool_calls", None)
        if calls is None:
            return 0
        return len(calls)

    def charge_message(self, message: Any) -> BudgetState:
        return self.charge(self.count_message_tool_calls(message))
