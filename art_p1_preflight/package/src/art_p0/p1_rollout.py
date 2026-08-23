"""P1 real-model rollout runner (ready-to-execute; used only for preflight here).

Runs one fresh-environment tau2 simulation under a chosen frozen harness and
budget, with the full logging schema required for P1 (identity / resource
availability / consumption / outcome / state / artifacts).

Reuses the P0.1-verified budget wrapper via `art_p0.harnesses` (h1/h2 subclass
it without changing enforcement).  Budget overflow remains a resource-infeasible
failure: `success_strict=False` whenever `budget_exceeded` (task constraint
§18 / P0.1 I7).  No P0.1 code path is modified.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from .budget import BudgetExceeded
from .harnesses import build_inner_agent, wrap_agent
from .ledger import RunLedger, RunRecord
from .state_hash import (
    environment_initial_state_hash,
    initialize_environment,
    task_initial_state_hash,
)
from .trajectory import TrajectoryStore, to_jsonable


@dataclass(frozen=True)
class P1RolloutSpec:
    task_id: str
    harness_id: str
    harness_hash: str
    condition_hash: str
    budget_level: str
    tool_budget_limit: int
    rollout_seed: int
    agent_model: str
    user_model: str
    reasoning_effort: str
    runtime_commit: str
    dataset_commit: str
    domain: str = "telecom"
    max_steps: int = 100
    agent_model_args: dict[str, Any] = field(default_factory=dict)
    user_model_args: dict[str, Any] = field(default_factory=dict)


def _role_of(msg: Any) -> str:
    role = getattr(msg, "role", "")
    return str(getattr(role, "value", role))


def _sum_usage(messages: list[Any]) -> dict[str, Optional[int]]:
    keys = ["prompt_tokens", "completion_tokens", "total_tokens",
            "reasoning_tokens", "cached_tokens"]
    agg = {k: 0 for k in keys}
    seen = {k: False for k in keys}
    for m in messages:
        usage = getattr(m, "usage", None)
        if usage is None:
            continue
        u = usage.model_dump() if hasattr(usage, "model_dump") else (
            dict(usage) if isinstance(usage, dict) else {}
        )
        # some providers nest reasoning/cached under details
        details = {}
        for dk in ("completion_tokens_details", "prompt_tokens_details"):
            dv = u.get(dk)
            if isinstance(dv, dict):
                details.update(dv)
        for k in keys:
            v = u.get(k)
            if v is None and k == "reasoning_tokens":
                v = details.get("reasoning_tokens")
            if v is None and k == "cached_tokens":
                v = details.get("cached_tokens")
            if isinstance(v, (int, float)):
                agg[k] += int(v)
                seen[k] = True
    return {k: (agg[k] if seen[k] else None) for k in keys}


def run_p1_rollout(
    spec: P1RolloutSpec,
    *,
    ledger: RunLedger,
    trajectory_store: TrajectoryStore,
    run_id: str,
) -> dict[str, Any]:
    """Execute one real-model rollout and return a full P1 log record.

    Constructs the real tau2 Orchestrator with a fresh environment, the frozen
    harness agent, and the pinned user simulator, then evaluates with the real
    grader. Requires tau2 + valid API credentials (caller must gate on creds).
    """
    from tau2.registry import registry
    from tau2.orchestrator.orchestrator import Orchestrator
    from tau2.runner import build_user, get_tasks, run_simulation
    from tau2.evaluator.evaluator import EvaluationType

    tasks = get_tasks(spec.domain, task_ids=[spec.task_id])
    if len(tasks) != 1:
        raise RuntimeError(f"expected 1 task {spec.task_id}, got {len(tasks)}")
    task = tasks[0]

    # Fresh environment per experimental unit (P0.1 I4).
    env = registry.get_env_constructor(spec.domain)()
    # State fingerprints (from a separately initialized fresh env).
    t_hash = task_initial_state_hash(task)
    e_hash = environment_initial_state_hash(
        initialize_environment(registry.get_env_constructor(spec.domain), task),
        domain=spec.domain,
    )

    agent_llm_args = dict(spec.agent_model_args)
    if spec.reasoning_effort:
        agent_llm_args.setdefault("reasoning_effort", spec.reasoning_effort)

    inner = build_inner_agent(
        spec.harness_id,
        tools=env.get_tools(),
        domain_policy=env.get_policy(),
        llm=spec.agent_model,
        llm_args=agent_llm_args,
    )
    agent = wrap_agent(inner, spec.harness_id, spec.tool_budget_limit)
    user = build_user(
        "user_simulator", env, task,
        llm=spec.user_model, llm_args=dict(spec.user_model_args),
    )

    orchestrator = Orchestrator(
        domain=spec.domain, agent=agent, user=user, environment=env, task=task,
        max_steps=spec.max_steps, seed=spec.rollout_seed, validate_communication=True,
    )

    record = RunRecord.new(
        task_id=str(task.id),
        harness_id=spec.harness_id,
        harness_hash=spec.harness_hash,
        resource_interface_id=f"tool_budget_{spec.tool_budget_limit}",
        seed=spec.rollout_seed,
        tool_budget_limit=spec.tool_budget_limit,
        metadata={
            "run_id": run_id,
            "condition_hash": spec.condition_hash,
            "budget_level": spec.budget_level,
            "agent_model": spec.agent_model,
            "user_model": spec.user_model,
            "reasoning_effort": spec.reasoning_effort,
            "runtime_commit": spec.runtime_commit,
            "dataset_commit": spec.dataset_commit,
            "max_steps": spec.max_steps,
            "tool_permissions_source": "env",
            "fresh_environment": True,
            "environment_object_id": id(env),
        },
    )
    record.run_id = run_id
    record.task_initial_state_hash = t_hash
    record.environment_initial_state_hash = e_hash

    result = None
    messages: list[Any] = []
    t0 = time.perf_counter()
    try:
        result = run_simulation(orchestrator, evaluation_type=EvaluationType.ALL)
        messages = list(getattr(result, "messages", []) or [])
        info = getattr(result, "reward_info", None)
        reward = float(getattr(info, "reward")) if info is not None and getattr(info, "reward", None) is not None else None
        record.success_official = (reward == 1.0) if reward is not None else None
        record.termination_reason = str(getattr(getattr(result, "termination_reason", None), "value", getattr(result, "termination_reason", None)))
        record.metadata["official_reward"] = reward
        record.cost_usd = float(getattr(result, "agent_cost", 0) or 0) + float(getattr(result, "user_cost", 0) or 0)
        record.metadata["agent_cost"] = getattr(result, "agent_cost", None)
        record.metadata["user_cost"] = getattr(result, "user_cost", None)
    except BudgetExceeded as exc:
        record.success_official = False
        record.budget_exceeded = True
        record.termination_reason = "ART_BUDGET_EXCEEDED"
        record.metadata["budget_error"] = {
            "requested": exc.requested, "remaining": exc.remaining,
            "used": exc.used, "limit": exc.limit,
        }
        if hasattr(orchestrator, "get_messages"):
            try:
                messages = list(orchestrator.get_messages() or [])
            except Exception:
                messages = list(getattr(orchestrator, "trajectory", []) or [])
    finally:
        state = getattr(orchestrator, "agent_state", None)
        record.tool_calls_used = int(getattr(state, "budget_used", 0) or 0)
        record.wall_seconds = time.perf_counter() - t0
        record.turns_used = sum(1 for m in messages if _role_of(m) == "assistant")
        # success_strict: budget overflow always fails (P0.1 I7 / §18)
        from .p1_config import ceiling_engaged, scientific_success_strict

        record.success_strict = scientific_success_strict(
            record.success_official, record.budget_exceeded
        )
        # Did the resource ceiling actually bind? (used == B) OR overflow
        record.metadata["ceiling_engaged"] = ceiling_engaged(
            record.tool_calls_used, record.tool_budget_limit, record.budget_exceeded
        )
        usage = _sum_usage(messages)
        record.input_tokens = usage["prompt_tokens"]
        record.output_tokens = usage["completion_tokens"]
        record.metadata["tokens"] = usage
        record.metadata["step_count"] = int(getattr(orchestrator, "step_count", 0) or 0)
        traj_path = trajectory_store.write(run_id, {
            "run_id": run_id,
            "task_id": record.task_id,
            "harness_id": spec.harness_id,
            "harness_hash": spec.harness_hash,
            "condition_hash": spec.condition_hash,
            "budget_level": spec.budget_level,
            "tool_budget_limit": spec.tool_budget_limit,
            "rollout_seed": spec.rollout_seed,
            "messages": messages,
            "reward_info": getattr(result, "reward_info", None),
            "termination_reason": record.termination_reason,
        })
        record.metadata["trajectory_path"] = str(traj_path)
        ledger.append(record)

    return asdict(record)
