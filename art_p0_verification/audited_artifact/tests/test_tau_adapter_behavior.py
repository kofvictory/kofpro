import pytest

from art_p0.budget import BudgetExceeded
from art_p0.fakes import FakeAssistantMessage, FakeToolCall
from art_p0.tau_adapter import BudgetEnforcingAgent


class Inner:
    tools = []
    domain_policy = "policy"

    def __init__(self, batches):
        self.batches = list(batches)

    def get_init_state(self, message_history=None):
        return {"i": 0, "history": message_history or []}

    def generate_next_message(self, message, state):
        n = self.batches[state["i"]]
        state = dict(state)
        state["i"] += 1
        msg = FakeAssistantMessage(
            tool_calls=[FakeToolCall(name=f"t{k}") for k in range(n)]
        )
        return msg, state


def test_wrapper_counts_and_rejects_atomically_without_tau_install():
    agent = BudgetEnforcingAgent(Inner([1, 2]), tool_budget=2)
    state = agent.get_init_state([])
    _, state = agent.generate_next_message(None, state)
    assert state.budget_used == 1
    with pytest.raises(BudgetExceeded):
        agent.generate_next_message(None, state)
    assert state.budget_used == 1
    assert state.budget_exceeded
