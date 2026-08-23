"""Current-τ³ runtime integration for P0 smoke and matrix experiments.

All tau2 imports are lazy so the package remains unit-testable without the
benchmark installed.  The integration follows the current public power-user API:
``get_tasks`` -> ``build_environment`` -> custom/wrapped agent -> ``build_user``
-> ``Orchestrator`` -> ``run_simulation``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Optional

from .budget import BudgetExceeded
from .hashing import harness_hash
from .ledger import RunLedger, RunRecord
from .tau_adapter import BudgetEnforcingAgent
from .trajectory import TrajectoryStore, to_jsonable


@dataclass(frozen=True)
class Tau3RunSpec:
    agent_llm: str
    user_llm: str
    tool_budget: int
    seed: int = 42
    task_id: str = "create_task_1"
    domain: str = "mock"
    harness_id: str = "h0_nominal"
    max_steps: int = 30
    max_errors: int = 5
    validate_communication: bool = True
    agent_llm_args: dict[str, Any] = field(default_factory=dict)
    user_llm_args: dict[str, Any] = field(default_factory=dict)


@dataclass
class Tau3RunArtifacts:
    record: RunRecord
    trajectory_path: Optional[Path]


def _sha256_json(value: Any) -> str:
    payload = json.dumps(
        to_jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _task_initial_state_fingerprint(task: Any) -> str:
    return _sha256_json(getattr(task, "initial_state", None))


def _role_of(msg: Any) -> str:
    role = getattr(msg, "role", "")
    return str(getattr(role, "value", role))


def _assistant_turns(messages: list[Any]) -> int:
    return sum(1 for m in messages if _role_of(m) == "assistant")


def _termination_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(getattr(value, "value", value))


def _reward_value(result: Any) -> Optional[float]:
    info = getattr(result, "reward_info", None)
    value = getattr(info, "reward", None) if info is not None else None
    return float(value) if value is not None else None


def _agent_cost(result: Any) -> Optional[float]:
    value = getattr(result, "agent_cost", None)
    return float(value) if value is not None else None


def _load_tau3_api() -> Any:  # pragma: no cover - requires tau2 install
    from types import SimpleNamespace

    from tau2.agent import LLMAgent
    from tau2.evaluator.evaluator import EvaluationType
    from tau2.orchestrator.orchestrator import Orchestrator
    from tau2.runner import build_environment, build_user, get_tasks, run_simulation

    return SimpleNamespace(
        LLMAgent=LLMAgent,
        EvaluationType=EvaluationType,
        Orchestrator=Orchestrator,
        build_environment=build_environment,
        build_user=build_user,
        get_tasks=get_tasks,
        run_simulation=run_simulation,
    )


def run_tau3_once(
    spec: Tau3RunSpec,
    *,
    ledger: RunLedger,
    trajectory_store: TrajectoryStore,
    api: Any = None,
) -> Tau3RunArtifacts:
    """Run one fresh-environment τ³ simulation and persist audit artifacts."""

    if spec.tool_budget < 0:
        raise ValueError("tool_budget must be non-negative")
    api = api or _load_tau3_api()

    tasks = api.get_tasks(spec.domain, task_ids=[spec.task_id])
    if len(tasks) != 1:
        raise RuntimeError(
            f"expected exactly one task {spec.domain}/{spec.task_id}, got {len(tasks)}"
        )
    task = tasks[0]

    # Scientific reset semantics: construct a fresh environment object for every
    # experimental unit. tau2's Orchestrator.initialize() then applies the task's
    # initial state through environment.set_state(...).
    env = api.build_environment(spec.domain)
    inner = api.LLMAgent(
        tools=env.get_tools(),
        domain_policy=env.get_policy(),
        llm=spec.agent_llm,
        llm_args=dict(spec.agent_llm_args),
    )
    agent = BudgetEnforcingAgent(inner_agent=inner, tool_budget=spec.tool_budget)
    user = api.build_user(
        "user_simulator",
        env,
        task,
        llm=spec.user_llm,
        llm_args=dict(spec.user_llm_args),
    )

    harness_cfg = {
        "kind": "nominal_tau3_llm_agent",
        "agent_llm": spec.agent_llm,
        "agent_llm_args": spec.agent_llm_args,
        "wrapper": "art_p0.BudgetEnforcingAgent",
        "overflow": "atomic_raise",
    }
    hhash = harness_hash(harness_cfg)
    record = RunRecord.new(
        task_id=str(task.id),
        harness_id=spec.harness_id,
        harness_hash=hhash,
        resource_interface_id=f"tool_budget_{spec.tool_budget}",
        seed=spec.seed,
        tool_budget_limit=spec.tool_budget,
        metadata={
            "domain": spec.domain,
            "agent_llm": spec.agent_llm,
            "user_llm": spec.user_llm,
            "fresh_environment": True,
            "environment_object_id": id(env),
            "task_initial_state_sha256": _task_initial_state_fingerprint(task),
        },
    )

    # P0.2 (O1): record separate task/env initial-state fingerprints. Guarded so
    # the P0.1 fake-`api` unit tests (whose fake env has no set_state/db) still
    # pass; on any failure the fields stay None rather than breaking the run.
    try:
        from . import state_hash as _sh

        record.task_initial_state_hash = _sh.task_initial_state_hash(task)
        try:
            _init_env = _sh.initialize_environment(
                lambda **kw: api.build_environment(spec.domain), task
            )
            record.environment_initial_state_hash = _sh.environment_initial_state_hash(
                _init_env, domain=spec.domain
            )
        except Exception:  # pragma: no cover - fake env in unit tests
            record.environment_initial_state_hash = None
    except Exception:  # pragma: no cover - defensive
        pass

    orchestrator = api.Orchestrator(
        domain=spec.domain,
        agent=agent,
        user=user,
        environment=env,
        task=task,
        max_steps=spec.max_steps,
        max_errors=spec.max_errors,
        seed=spec.seed,
        validate_communication=spec.validate_communication,
    )

    result = None
    messages: list[Any] = []
    t0 = time.perf_counter()
    try:
        result = api.run_simulation(
            orchestrator,
            evaluation_type=api.EvaluationType.ALL,
        )
        messages = list(getattr(result, "messages", []) or [])
        reward = _reward_value(result)
        record.success_official = reward == 1.0 if reward is not None else None
        record.termination_reason = _termination_value(
            getattr(result, "termination_reason", None)
        )
        record.turns_used = _assistant_turns(messages)
        record.cost_usd = _agent_cost(result)
        record.metadata["official_reward"] = reward
    except BudgetExceeded as exc:
        # An action that attempts an unavailable resource is infeasible under this
        # resource interface, even if earlier environment state happens to satisfy
        # part of the task. Treat the rollout as a resource-exhaustion failure.
        record.success_official = False
        record.budget_exceeded = True
        record.termination_reason = "ART_BUDGET_EXCEEDED"
        record.metadata["budget_error"] = {
            "requested": exc.requested,
            "remaining": exc.remaining,
            "used": exc.used,
            "limit": exc.limit,
        }
        if hasattr(orchestrator, "get_messages"):
            messages = list(orchestrator.get_messages() or [])
        elif hasattr(orchestrator, "trajectory"):
            messages = list(orchestrator.trajectory or [])
        record.turns_used = _assistant_turns(messages)
    finally:
        state = getattr(orchestrator, "agent_state", None)
        record.tool_calls_used = int(getattr(state, "budget_used", 0) or 0)
        record.wall_seconds = time.perf_counter() - t0
        record.metadata["step_count"] = int(
            getattr(orchestrator, "step_count", 0) or 0
        )
        record.metadata["orchestrator_termination_reason"] = _termination_value(
            getattr(orchestrator, "termination_reason", None)
        )

        trajectory_path = trajectory_store.write(
            record.run_id,
            {
                "run_id": record.run_id,
                "task_id": record.task_id,
                "harness_hash": record.harness_hash,
                "resource_interface_id": record.resource_interface_id,
                "messages": messages,
                "reward_info": getattr(result, "reward_info", None),
                "termination_reason": record.termination_reason,
            },
        )
        record.metadata["trajectory_path"] = str(trajectory_path)
        ledger.append(record)

    return Tau3RunArtifacts(record=record, trajectory_path=trajectory_path)


def check_matrix_invariants(records: list[RunRecord]) -> list[str]:
    """Return human-readable invariant violations; empty means PASS."""

    errors: list[str] = []
    if not records:
        return ["no records"]

    if len({r.harness_hash for r in records}) != 1:
        errors.append("harness hash changed across resource budgets")
    if len({r.task_id for r in records}) != 1:
        errors.append("task changed across resource budgets")
    if len({r.seed for r in records}) != 1:
        errors.append("seed changed across resource budgets")
    if len({r.metadata.get("task_initial_state_sha256") for r in records}) != 1:
        errors.append("task initial-state fingerprint changed across runs")
    if len({r.metadata.get("environment_object_id") for r in records}) != len(records):
        errors.append("fresh environment object was not created for every run")

    for r in records:
        if r.tool_calls_used > r.tool_budget_limit:
            errors.append(
                f"{r.run_id}: used {r.tool_calls_used} > limit {r.tool_budget_limit}"
            )
        if r.budget_exceeded and r.success_official is not False:
            errors.append(f"{r.run_id}: budget overflow must be an infeasible failure")
        if not r.metadata.get("trajectory_path"):
            errors.append(f"{r.run_id}: missing trajectory path")

    return errors
