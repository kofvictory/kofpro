#!/usr/bin/env python3
"""Phase 4 — real tau runtime mock integration for ART P0 (no LLM).

This driver runs the ART P0 budget matrix (B in {1,2,4}) on the *real* tau2
Orchestrator / Environment / evaluator, using deterministic scripted
participants injected through the ART-provided ``api`` seam of
``art_p0.tau3_runtime.run_tau3_once``.

Nothing in the ART package (``src/art_p0/**``) is modified.  The only thing
replaced relative to a production run is the *policy source*: instead of an
LLM-backed ``LLMAgent`` / ``UserSimulator`` we inject fixed, budget-independent
scripted policies so the run is reproducible and free of API keys.  Everything
else -- task loading, environment construction, initial-state application,
turn routing, tool execution, termination, and DB-based reward evaluation --
is the genuine tau2 machinery at the pinned commit.

The scripted agent's action sequence is identical at every budget (README
invariant 3: "no hidden policy mutation"); only the ART ToolCallBudget ceiling
differs, so the matrix exercises the true nested-budget semantics.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

# Real tau2 machinery
from tau2.agent.base_agent import HalfDuplexAgent
from tau2.user.user_simulator_base import HalfDuplexUser
from tau2.data_model.message import AssistantMessage, ToolCall, UserMessage
from tau2.evaluator.evaluator import EvaluationType
from tau2.orchestrator.orchestrator import Orchestrator
from tau2.runner import build_environment, build_user, get_tasks, run_simulation
from tau2.environment.environment import Environment

# ART P0 (unmodified)
from art_p0.ledger import RunLedger
from art_p0.trajectory import TrajectoryStore
from art_p0.tau3_runtime import Tau3RunSpec, check_matrix_invariants, run_tau3_once
from art_p0.budget import BudgetExceeded
from art_p0.tau_adapter import BudgetEnforcingAgent


# --------------------------------------------------------------------------
# Deterministic, budget-independent scripted participants (no LLM)
# --------------------------------------------------------------------------
class ScriptedAgentState:
    def __init__(self) -> None:
        self.turn = 0


class ScriptedAgent(HalfDuplexAgent):
    """Fixed policy: one tool call per agent turn, then a closing text turn.

    Planned actions (identical for every budget):
      turn 0: create_task(user_1, 'Important Meeting')   [gold action]
      turn 1: get_users()
      turn 2: get_users()
      turn 3: text -> "created successfully" (hands back to the user)

    The wrapper (art_p0.BudgetEnforcingAgent) is the ONLY thing that enforces a
    ceiling; this policy never inspects the budget, so a batch rejected at a low
    budget is byte-for-byte the same action that a higher budget would accept.
    """

    # Accept the same ctor kwargs the runtime passes to LLMAgent so it can be
    # slotted in through the `api.LLMAgent` seam unchanged.
    def __init__(self, tools, domain_policy, llm=None, llm_args=None):
        super().__init__(tools=tools, domain_policy=domain_policy)
        self.llm = llm
        self.llm_args = dict(llm_args or {})

    def get_init_state(self, message_history=None) -> ScriptedAgentState:
        return ScriptedAgentState()

    def _plan(self, turn: int) -> AssistantMessage:
        if turn == 0:
            return AssistantMessage(
                role="assistant",
                tool_calls=[
                    ToolCall(
                        id="call_create_1",
                        name="create_task",
                        arguments={"user_id": "user_1", "title": "Important Meeting"},
                    )
                ],
            )
        if turn in (1, 2):
            return AssistantMessage(
                role="assistant",
                tool_calls=[ToolCall(id=f"call_getusers_{turn}", name="get_users", arguments={})],
            )
        return AssistantMessage(
            role="assistant",
            content="Your task 'Important Meeting' has been created successfully. Anything else?",
        )

    def generate_next_message(self, message, state: ScriptedAgentState):
        msg = self._plan(state.turn)
        state.turn += 1
        return msg, state


class ScriptedUserState:
    def __init__(self) -> None:
        self.turn = 0


class ScriptedUser(HalfDuplexUser):
    """Fixed user: issue the request once, then stop when the agent replies."""

    def __init__(self, instructions=None, tools=None, llm=None, llm_args=None, **kw):
        super().__init__(instructions=instructions, tools=tools)
        self.llm = llm

    def get_init_state(self, message_history=None) -> ScriptedUserState:
        return ScriptedUserState()

    def generate_next_message(self, message, state: ScriptedUserState):
        state.turn += 1
        if state.turn == 1:
            out = UserMessage(
                role="user",
                content="Please create a task called 'Important Meeting' for user_1.",
            )
        else:
            # Any content containing the tau2 stop token terminates the sim
            # via UserSimulator.is_stop(...) inside the real orchestrator.
            out = UserMessage(role="user", content="Great, thank you. ###STOP###")
        return out, state


def _scripted_build_user(user_name, environment, task, *, llm=None, llm_args=None, **kw):
    return ScriptedUser(instructions=str(task.user_scenario), llm=llm, llm_args=llm_args)


def make_api() -> SimpleNamespace:
    """Real tau2 api with only the *policy* sources swapped for scripted ones."""
    return SimpleNamespace(
        LLMAgent=ScriptedAgent,          # scripted, no LLM
        build_user=_scripted_build_user,  # scripted, no LLM
        get_tasks=get_tasks,              # REAL
        build_environment=build_environment,  # REAL
        Orchestrator=Orchestrator,        # REAL
        run_simulation=run_simulation,    # REAL
        EvaluationType=EvaluationType,    # REAL (ALL == DB+COMMUNICATE for this task)
    )


# --------------------------------------------------------------------------
# Explicit I2 probe: multi-call batch atomicity on the REAL environment
# --------------------------------------------------------------------------
class BatchAgent(HalfDuplexAgent):
    """Emits a single message containing a batch of TWO tool calls."""

    def __init__(self, tools, domain_policy, llm=None, llm_args=None):
        super().__init__(tools=tools, domain_policy=domain_policy)

    def get_init_state(self, message_history=None):
        return {"turn": 0}

    def generate_next_message(self, message, state):
        state["turn"] += 1
        msg = AssistantMessage(
            role="assistant",
            tool_calls=[
                ToolCall(id="b1", name="create_task",
                         arguments={"user_id": "user_1", "title": "Important Meeting"}),
                ToolCall(id="b2", name="get_users", arguments={}),
            ],
        )
        return msg, state


def probe_atomic_overflow() -> dict:
    """At B=1, a 2-call batch must be rejected WITHOUT executing either call.

    We verify against the real mock environment DB that no task was created.
    """
    env: Environment = build_environment("mock")
    tasks_before = {uid: list(u.tasks) for uid, u in env.tools.db.users.items()}
    inner = BatchAgent(tools=env.get_tools(), domain_policy=env.get_policy())
    agent = BudgetEnforcingAgent(inner_agent=inner, tool_budget=1)
    state = agent.get_init_state()
    raised = False
    try:
        # Ask the wrapped agent to produce its next message; the batch of 2
        # exceeds the remaining budget of 1 and must raise atomically.
        agent.generate_next_message(UserMessage(role="user", content="go"), state)
    except BudgetExceeded as exc:
        raised = True
        err = {"requested": exc.requested, "remaining": exc.remaining,
               "used": exc.used, "limit": exc.limit}
    tasks_after = {uid: list(u.tasks) for uid, u in env.tools.db.users.items()}
    return {
        "raised": raised,
        "error": err if raised else None,
        "budget_used_after": state.budget_used,
        "db_unchanged": tasks_before == tasks_after,
        "tasks_before": tasks_before,
        "tasks_after": tasks_after,
    }


def main() -> int:
    runs_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("runs")
    runs_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = runs_dir / "p0_real_matrix.jsonl"
    traj_dir = runs_dir / "trajectories"
    # start clean so the ledger reflects only this run
    if ledger_path.exists():
        ledger_path.unlink()
    ledger = RunLedger(ledger_path)
    store = TrajectoryStore(traj_dir)
    api = make_api()

    budgets = [1, 2, 4]
    records = []
    print("=== Phase 4: real tau Orchestrator, scripted (no-LLM) policies ===")
    for b in budgets:
        art = run_tau3_once(
            Tau3RunSpec(
                agent_llm="scripted/none",
                user_llm="scripted/none",
                tool_budget=b,
                seed=42,
                task_id="create_task_1",
                domain="mock",
                max_steps=30,
            ),
            ledger=ledger,
            trajectory_store=store,
            api=api,
        )
        r = art.record
        records.append(r)
        print(
            f"B={b}: used={r.tool_calls_used}/{r.tool_budget_limit} "
            f"exceeded={r.budget_exceeded} reward={r.metadata.get('official_reward')} "
            f"success={r.success_official} term={r.termination_reason} "
            f"init_state_sha={r.metadata.get('task_initial_state_sha256')[:12]} "
            f"harness={r.harness_hash[:12]} traj={'yes' if r.metadata.get('trajectory_path') else 'no'}"
        )

    print("\n=== check_matrix_invariants (ART built-in) ===")
    errors = check_matrix_invariants(records)
    print("PASS" if not errors else "FAIL")
    for e in errors:
        print("  -", e)

    print("\n=== Explicit invariant assertions (real runtime) ===")
    checks = {}
    # I1: n_tool_used <= B
    checks["I1_budget_ceiling"] = all(r.tool_calls_used <= r.tool_budget_limit for r in records)
    # I3: identical initial-state hash across budgets
    checks["I3_initial_state_equal"] = len({r.metadata.get("task_initial_state_sha256") for r in records}) == 1
    # I4: fresh environment object per run
    checks["I4_fresh_env"] = len({r.metadata.get("environment_object_id") for r in records}) == len(records)
    # I5: identical harness hash across budgets
    checks["I5_harness_equal"] = len({r.harness_hash for r in records}) == 1
    # I6: ledger + trajectory persisted
    checks["I6_persistence"] = ledger_path.exists() and all(
        Path(r.metadata["trajectory_path"]).exists() for r in records
    )
    # I7: any budget-exceeded run is an official failure
    checks["I7_infeasible_is_failure"] = all(
        (not r.budget_exceeded) or (r.budget_exceeded and r.success_official is False)
        for r in records
    )
    # Nested feasibility: used is monotonic non-decreasing in budget for same policy
    used_by_b = [r.tool_calls_used for r in sorted(records, key=lambda x: x.tool_budget_limit)]
    checks["nested_monotonic_used"] = used_by_b == sorted(used_by_b)

    # I2: atomic multi-call batch overflow on the real environment
    probe = probe_atomic_overflow()
    checks["I2_atomic_overflow_raised"] = probe["raised"]
    checks["I2_atomic_no_partial_exec"] = probe["db_unchanged"] and probe["budget_used_after"] == 0
    print(json.dumps({"atomic_overflow_probe": probe}, indent=2, default=str))

    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")

    # Persist a machine-readable summary
    summary = {
        "commit_pinned": "a2c024725189473d2d7cea3a5cfdbcc67478e41f",
        "budgets": budgets,
        "records": [
            {
                "budget": r.tool_budget_limit,
                "tool_calls_used": r.tool_calls_used,
                "official_reward": r.metadata.get("official_reward"),
                "budget_exceeded": r.budget_exceeded,
                "success_official": r.success_official,
                "termination_reason": r.termination_reason,
                "orchestrator_termination_reason": r.metadata.get("orchestrator_termination_reason"),
                "step_count": r.metadata.get("step_count"),
                "initial_state_sha256": r.metadata.get("task_initial_state_sha256"),
                "harness_hash": r.harness_hash,
                "environment_object_id": r.metadata.get("environment_object_id"),
                "trajectory_path": r.metadata.get("trajectory_path"),
                "run_id": r.run_id,
            }
            for r in records
        ],
        "matrix_invariants_errors": errors,
        "explicit_checks": checks,
        "atomic_overflow_probe": probe,
    }
    (runs_dir / "phase4_summary.json").write_text(
        json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8"
    )
    print(f"\nsummary -> {runs_dir / 'phase4_summary.json'}")
    print(f"ledger  -> {ledger_path}")

    all_ok = (not errors) and all(checks.values())
    print("\nPHASE4=" + ("PASS" if all_ok else "FAIL"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
