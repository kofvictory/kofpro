from pathlib import Path
from types import SimpleNamespace

from art_p0.fakes import FakeAssistantMessage, FakeToolCall
from art_p0.ledger import RunLedger
from art_p0.tau3_runtime import Tau3RunSpec, check_matrix_invariants, run_tau3_once
from art_p0.trajectory import TrajectoryStore


class FakeTask:
    id = "create_task_1"
    initial_state = {"db": {"tasks": []}}


class FakeEnv:
    next_id = 0

    def __init__(self):
        type(self).next_id += 1
        self.instance = type(self).next_id

    def get_tools(self):
        return []

    def get_policy(self):
        return "policy"


class FakeInnerAgent:
    def __init__(self, tools, domain_policy, llm, llm_args):
        self.tools = tools
        self.domain_policy = domain_policy
        self.batches = list(llm_args.get("batches", [1]))

    def get_init_state(self, message_history=None):
        return {"i": 0}

    def generate_next_message(self, message, state):
        i = state["i"]
        n = self.batches[min(i, len(self.batches) - 1)]
        state = {"i": i + 1}
        return FakeAssistantMessage(
            tool_calls=[FakeToolCall(name=f"t{k}") for k in range(n)]
        ), state

    def set_seed(self, seed):
        self.seed = seed

    def stop(self, message, state):
        pass


class FakeUser:
    def set_seed(self, seed):
        self.seed = seed

    def stop(self, message, state):
        pass


class FakeRewardInfo:
    reward = 1.0


class FakeResult:
    def __init__(self, messages, termination_reason="agent_stop"):
        self.messages = messages
        self.reward_info = FakeRewardInfo()
        self.agent_cost = 0.01
        self.termination_reason = termination_reason


class FakeOrchestrator:
    def __init__(self, *, agent, **kwargs):
        self.agent = agent
        self.agent_state = None
        self.step_count = 0
        self.termination_reason = None
        self.trajectory = []

    def get_messages(self):
        return self.trajectory


class FakeEvaluationType:
    ALL = "all"


def make_api():
    def get_tasks(domain, task_ids):
        return [FakeTask()]

    def build_environment(domain):
        return FakeEnv()

    def build_user(name, env, task, llm, llm_args):
        return FakeUser()

    def run_simulation(orchestrator, evaluation_type):
        state = orchestrator.agent.get_init_state([])
        msg, state = orchestrator.agent.generate_next_message(None, state)
        orchestrator.agent_state = state
        orchestrator.trajectory.append(msg)
        orchestrator.step_count = 1
        return FakeResult(list(orchestrator.trajectory))

    return SimpleNamespace(
        LLMAgent=FakeInnerAgent,
        EvaluationType=FakeEvaluationType,
        Orchestrator=FakeOrchestrator,
        get_tasks=get_tasks,
        build_environment=build_environment,
        build_user=build_user,
        run_simulation=run_simulation,
    )


def test_run_tau3_once_persists_ledger_and_trajectory(tmp_path):
    art = run_tau3_once(
        Tau3RunSpec(
            agent_llm="fake",
            user_llm="fake",
            tool_budget=2,
            agent_llm_args={"batches": [1]},
        ),
        ledger=RunLedger(tmp_path / "runs.jsonl"),
        trajectory_store=TrajectoryStore(tmp_path / "traj"),
        api=make_api(),
    )
    assert art.record.tool_calls_used == 1
    assert art.record.success_official is True
    assert art.record.cost_usd == 0.01
    assert art.trajectory_path.exists()


def test_budget_overflow_is_recorded_as_infeasible_failure(tmp_path):
    art = run_tau3_once(
        Tau3RunSpec(
            agent_llm="fake",
            user_llm="fake",
            tool_budget=1,
            agent_llm_args={"batches": [2]},
        ),
        ledger=RunLedger(tmp_path / "runs.jsonl"),
        trajectory_store=TrajectoryStore(tmp_path / "traj"),
        api=make_api(),
    )
    assert art.record.budget_exceeded is True
    assert art.record.tool_calls_used == 0
    assert art.record.success_official is False
    assert art.record.termination_reason == "ART_BUDGET_EXCEEDED"


def test_matrix_invariants_accept_fresh_env_same_task_seed_harness(tmp_path):
    records = []
    for b in (1, 2, 4):
        art = run_tau3_once(
            Tau3RunSpec(
                agent_llm="fake",
                user_llm="fake",
                tool_budget=b,
                seed=7,
                agent_llm_args={"batches": [1]},
            ),
            ledger=RunLedger(tmp_path / "runs.jsonl"),
            trajectory_store=TrajectoryStore(tmp_path / "traj"),
            api=make_api(),
        )
        records.append(art.record)
    assert check_matrix_invariants(records) == []
