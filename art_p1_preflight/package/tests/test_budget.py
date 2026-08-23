import pytest

from art_p0.budget import BudgetExceeded, BudgetState, ToolCallBudget
from art_p0.fakes import FakeAssistantMessage, FakeToolCall


def msg(n):
    return FakeAssistantMessage(tool_calls=[FakeToolCall(name=f"t{i}") for i in range(n)])


def test_budget_state_spend_and_remaining():
    s = BudgetState(limit=4)
    s = s.spend(3)
    assert s.used == 3
    assert s.remaining == 1


def test_atomic_overflow_does_not_mutate_budget():
    b = ToolCallBudget(4)
    b.charge_message(msg(3))
    with pytest.raises(BudgetExceeded) as exc:
        b.charge_message(msg(2))
    assert exc.value.requested == 2
    assert exc.value.remaining == 1
    assert b.used == 3
    assert b.remaining == 1


def test_zero_tool_message_costs_zero():
    b = ToolCallBudget(2)
    b.charge_message(FakeAssistantMessage(content="hello"))
    assert b.used == 0


def test_nested_budget_feasibility_for_same_sequence():
    sequence = [msg(1), msg(2), msg(1)]
    low = ToolCallBudget(4)
    high = ToolCallBudget(8)
    for m in sequence:
        low.charge_message(m)
        high.charge_message(m)
    assert low.used == high.used == 4
    assert high.remaining > low.remaining
