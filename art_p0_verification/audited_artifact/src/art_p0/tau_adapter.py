"""Thin adapter for current τ³-bench half-duplex agents.

The core instrumentation is benchmark-independent.  When ``tau2`` is installed,
``BudgetEnforcingAgent`` subclasses its current ``HalfDuplexAgent``.  When it is
not installed, the same wrapper remains usable in contract/unit tests with fake
agents; no benchmark code or LLM key is required.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .budget import BudgetExceeded, ToolCallBudget

try:  # pragma: no cover - exercised only inside a tau2 environment
    from tau2.agent.base_agent import HalfDuplexAgent
except ImportError:  # pragma: no cover
    HalfDuplexAgent = object  # type: ignore[misc,assignment]


@dataclass
class BudgetWrappedState:
    inner_state: Any
    budget_used: int
    budget_exceeded: bool = False


class BudgetEnforcingAgent(HalfDuplexAgent):  # type: ignore[misc]
    """Wrap a half-duplex agent with a hard atomic tool-call ceiling.

    If the inner agent emits a batch that does not fit, ``BudgetExceeded`` is
    raised before the orchestrator can execute *any* call in that batch.  The
    wrapper never truncates or rewrites the inner policy's chosen action.
    """

    def __init__(self, inner_agent: Any, tool_budget: int):
        if tool_budget < 0:
            raise ValueError("tool_budget must be non-negative")
        if HalfDuplexAgent is object:
            # Contract-test mode: keep the public fields expected by tau2 without
            # requiring tau2 itself to be installed.
            self.tools = getattr(inner_agent, "tools", [])
            self.domain_policy = getattr(inner_agent, "domain_policy", "")
        else:  # pragma: no cover - executed in pinned tau2 environment
            super().__init__(
                tools=inner_agent.tools,
                domain_policy=inner_agent.domain_policy,
            )
        self.inner_agent = inner_agent
        self.tool_budget = int(tool_budget)

    def get_init_state(
        self, message_history: Optional[list[Any]] = None
    ) -> BudgetWrappedState:
        inner = self.inner_agent.get_init_state(message_history=message_history)
        return BudgetWrappedState(inner_state=inner, budget_used=0)

    def generate_next_message(self, message: Any, state: BudgetWrappedState):
        response, inner_state = self.inner_agent.generate_next_message(
            message, state.inner_state
        )
        n = ToolCallBudget.count_message_tool_calls(response)
        remaining = self.tool_budget - state.budget_used
        if n > remaining:
            state.inner_state = inner_state
            state.budget_exceeded = True
            raise BudgetExceeded(
                requested=n,
                remaining=remaining,
                used=state.budget_used,
                limit=self.tool_budget,
            )
        state.inner_state = inner_state
        state.budget_used += n
        return response, state

    def set_seed(self, seed: int) -> None:
        if hasattr(self.inner_agent, "set_seed"):
            self.inner_agent.set_seed(seed)

    def stop(
        self, message: Any = None, state: Optional[BudgetWrappedState] = None
    ) -> None:
        inner_state = state.inner_state if state is not None else None
        if hasattr(self.inner_agent, "stop"):
            self.inner_agent.stop(message, inner_state)
