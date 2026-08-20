"""Five-probe TaskValidator pipeline against the real tau2 evaluator (P0.2).

Each candidate task ``x`` is audited with five probes:

* **gold**        -- does the benchmark's own reference behavior actually PASS?
* **noop**        -- does doing nothing (wrongly) PASS a task that requires action?
* **omission**    -- can the grader DETECT dropping a required step?
* **alternative** -- is a semantically-equivalent different route unfairly REJECTED?
* **policy**      -- do task / policy / tools / initial-state / evaluator agree?

The probes synthesize trajectories and grade them with the *real*
``tau2.evaluator.evaluate_simulation`` at the pinned runtime commit -- no LLM and
no Orchestrator, so the P0.1 budget path is untouched.  For the Telecom ``base``
split this is fully deterministic (every task is graded on ENV_ASSERTION /
ACTION only; no NL judge).

Scientific guardrails baked in (task constraints 1-6):
  * task validity is never defined by benchmark reward alone -- gold PASS is
    necessary but the admission rule also requires noop-negative,
    omission-detectable, and policy-consistent;
  * the reference action list is not assumed to be the only correct trajectory
    (alternative probe) nor assumed individually necessary (omission probe
    measures which actions are *load-bearing* empirically);
  * no-op false positives and invalid-trajectory acceptance are actively hunted.
"""
from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from types import SimpleNamespace
from typing import Any, Optional

from .state_hash import (
    environment_initial_state_hash,
    initialize_environment,
    task_initial_state_hash,
)

# ---- probe status vocabulary ------------------------------------------------
PASS = "PASS"
FAIL = "FAIL"
DETECTED = "DETECTED"
NOT_DETECTED = "NOT_DETECTED"
NOT_CONSTRUCTIBLE = "NOT_CONSTRUCTIBLE"
NA = "N/A"

# ---- exclusion reason codes -------------------------------------------------
GOLD_FAIL = "GOLD_FAIL"
NOOP_FALSE_POSITIVE = "NOOP_FALSE_POSITIVE"
OMISSION_NOT_DETECTED = "OMISSION_NOT_DETECTED"
POLICY_MISMATCH = "POLICY_MISMATCH"
AMBIGUOUS = "AMBIGUOUS"
IMPOSSIBLE = "IMPOSSIBLE"
GRADER_OVERCONSTRAINED = "GRADER_OVERCONSTRAINED"
MANUAL_REVIEW = "MANUAL_REVIEW"


@dataclass
class ProbeOutcome:
    name: str
    status: str
    reward: Optional[float] = None
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskValidation:
    task_id: str
    domain: str
    task_class: str  # "normal" | "refusal"
    runtime_commit: Optional[str]
    verified_dataset_commit: Optional[str]
    gold: ProbeOutcome
    noop: ProbeOutcome
    omission: ProbeOutcome
    alternative: ProbeOutcome
    policy: ProbeOutcome
    official_gold_reward: Optional[float]
    strict_gold_reward: Optional[float]
    success_official: Optional[bool]
    success_strict: Optional[bool]
    strict_conditions: dict[str, Any]
    task_initial_state_hash: Optional[str]
    environment_initial_state_hash: Optional[str]
    reward_basis: list[str]
    admitted: bool
    exclusion_reason: Optional[str]
    manual_review_required: bool
    failure_reason: Optional[str]
    flags: list[str] = field(default_factory=list)

    def to_row(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "domain": self.domain,
            "task_class": self.task_class,
            "runtime_commit": self.runtime_commit,
            "verified_dataset_commit": self.verified_dataset_commit,
            "gold_pass": self.gold.status == PASS,
            "noop_pass": self.noop.status == PASS,
            "omission_detected": self.omission.status == DETECTED,
            "alternative_valid_pass": self.alternative.status,
            "policy_consistent": self.policy.status == PASS,
            "official_gold_reward": self.official_gold_reward,
            "strict_gold_reward": self.strict_gold_reward,
            "success_official": self.success_official,
            "success_strict": self.success_strict,
            "task_initial_state_hash": self.task_initial_state_hash,
            "environment_initial_state_hash": self.environment_initial_state_hash,
            "reward_basis": self.reward_basis,
            "admitted": self.admitted,
            "failure_reason": self.failure_reason,
            "exclusion_reason": self.exclusion_reason,
            "manual_review_required": self.manual_review_required,
            "flags": self.flags,
        }


class TelecomProbeRunner:
    """LLM-free probe runner bound to a tau2 domain (default: telecom)."""

    def __init__(
        self,
        domain: str = "telecom",
        *,
        runtime_commit: Optional[str] = None,
        verified_dataset_commit: Optional[str] = None,
        evaluation_type: Any = None,
    ):
        # Lazy tau2 imports so the package stays importable without the benchmark.
        from tau2.registry import registry
        from tau2.data_model.message import AssistantMessage, ToolCall, ToolMessage, UserMessage
        from tau2.data_model.simulation import SimulationRun
        from tau2.data_model.tasks import RewardType
        from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation
        from tau2.orchestrator.orchestrator import TerminationReason

        self.domain = domain
        self.registry = registry
        self.env_constructor = registry.get_env_constructor(domain)
        self._M = SimpleNamespace(
            AssistantMessage=AssistantMessage,
            UserMessage=UserMessage,
            ToolCall=ToolCall,
            ToolMessage=ToolMessage,
            SimulationRun=SimulationRun,
            RewardType=RewardType,
            EvaluationType=EvaluationType,
            evaluate_simulation=evaluate_simulation,
            TerminationReason=TerminationReason,
        )
        self.evaluation_type = evaluation_type or EvaluationType.ALL
        self.runtime_commit = runtime_commit
        self.verified_dataset_commit = verified_dataset_commit

    # -- low-level helpers ----------------------------------------------------
    def _init_env(self, task: Any) -> Any:
        return initialize_environment(self.env_constructor, task)

    def _is_mutating(self, env: Any, name: str) -> bool:
        try:
            return bool(env._is_mutating_tool(name))
        except Exception:
            return True  # conservative: treat unknown as mutating

    def _build_trajectory(self, task: Any, actions: list[Any]) -> list[Any]:
        """Render an ordered action list into a gradeable message trajectory.

        Tool-result contents are produced by executing each action on a fresh,
        identically-initialized environment in order, so the evaluator's strict
        replay (on its own fresh env) reproduces identical contents.
        """
        M = self._M
        env = self._init_env(task)
        traj: list[Any] = []
        for i, a in enumerate(actions):
            tc = M.ToolCall(
                id=f"probe_{i}",
                name=a.name,
                arguments=dict(a.arguments),
                requestor=a.requestor,
            )
            tm = env.get_response(tc)  # executes + mutates scratch env
            if a.requestor == "user":
                traj.append(M.UserMessage(role="user", tool_calls=[tc]))
            else:
                traj.append(M.AssistantMessage(role="assistant", tool_calls=[tc]))
            traj.append(tm)
        return traj

    def _grade(self, task: Any, trajectory: list[Any]) -> Any:
        M = self._M
        sim = M.SimulationRun(
            id="probe",
            task_id=str(task.id),
            start_time="t",
            end_time="t",
            duration=0.0,
            termination_reason=M.TerminationReason.USER_STOP,
            messages=trajectory,
            seed=42,
        )
        return M.evaluate_simulation(
            simulation=sim,
            task=task,
            evaluation_type=self.evaluation_type,
            solo_mode=False,
            domain=self.domain,
        )

    @staticmethod
    def _reward(ri: Any) -> Optional[float]:
        r = getattr(ri, "reward", None)
        return float(r) if r is not None else None

    # -- probes ---------------------------------------------------------------
    def probe_gold(self, task: Any) -> ProbeOutcome:
        actions = list(task.evaluation_criteria.actions or [])
        try:
            traj = self._build_trajectory(task, actions)
            ri = self._grade(task, traj)
        except Exception as exc:
            return ProbeOutcome("gold", FAIL, None, {"error": repr(exc)})
        reward = self._reward(ri)
        status = PASS if reward == 1.0 else FAIL
        env_asserts = [
            {"func": c.env_assertion.func_name, "met": bool(c.met)}
            for c in (getattr(ri, "env_assertions", None) or [])
        ]
        action_checks = [
            {"name": c.action.name, "match": bool(c.action_match)}
            for c in (getattr(ri, "action_checks", None) or [])
        ]
        return ProbeOutcome(
            "gold",
            status,
            reward,
            {
                "n_actions": len(actions),
                "env_assertions": env_asserts,
                "action_checks": action_checks,
                "reward_breakdown": {
                    str(k): v for k, v in (getattr(ri, "reward_breakdown", None) or {}).items()
                },
            },
        )

    def probe_noop(self, task: Any) -> ProbeOutcome:
        """Empty trajectory. PASS == the task does NOT pass with no action."""
        try:
            ri = self._grade(task, [])
        except Exception as exc:
            return ProbeOutcome("noop", NA, None, {"error": repr(exc)})
        reward = self._reward(ri)
        # PASS means the no-op did not achieve reward 1 (no false positive).
        status = PASS if reward != 1.0 else FAIL
        return ProbeOutcome("noop", status, reward, {"noop_reward": reward})

    def probe_omission(self, task: Any) -> ProbeOutcome:
        """Drop each mutating reference action once; detect grader sensitivity.

        DETECTED  == at least one single mutating-action removal drops reward
                     below 1 (a genuinely load-bearing step whose absence the
                     grader catches).
        NOT_DETECTED == the task has >=1 mutating action but no single removal
                     is caught (grader insensitive or actions redundant).
        """
        actions = list(task.evaluation_criteria.actions or [])
        env = self._init_env(task)
        mut_idx = [i for i, a in enumerate(actions) if self._is_mutating(env, a.name)]
        if not mut_idx:
            return ProbeOutcome(
                "omission", NA, None, {"note": "no mutating reference actions"}
            )
        load_bearing = []
        per_action = []
        for i in mut_idx:
            reduced = [a for j, a in enumerate(actions) if j != i]
            try:
                ri = self._grade(task, self._build_trajectory(task, reduced))
                reward = self._reward(ri)
            except Exception as exc:
                reward = None
                per_action.append({"dropped": actions[i].name, "error": repr(exc)})
                continue
            caught = reward is not None and reward < 1.0
            per_action.append(
                {"dropped_index": i, "dropped": actions[i].name, "reward": reward, "detected": caught}
            )
            if caught:
                load_bearing.append(actions[i].name)
        status = DETECTED if load_bearing else NOT_DETECTED
        return ProbeOutcome(
            "omission",
            status,
            None,
            {"load_bearing_actions": load_bearing, "per_action": per_action, "n_mutating": len(mut_idx)},
        )

    def probe_alternative(self, task: Any) -> ProbeOutcome:
        """A different-but-valid route must not be rejected.

        Constructs a reordered route over the mutating reference actions and
        grades it. PASS only when that genuinely different route still reaches
        reward 1 (verified against the task's own end-state assertions -- not
        fabricated). When no safe alternate route exists (< 2 mutating actions,
        or reorder does not reach the asserted end state), reports
        NOT_CONSTRUCTIBLE rather than guessing.
        """
        actions = list(task.evaluation_criteria.actions or [])
        env = self._init_env(task)
        mut_idx = [i for i, a in enumerate(actions) if self._is_mutating(env, a.name)]
        if len(mut_idx) < 2:
            return ProbeOutcome(
                "alternative",
                NOT_CONSTRUCTIBLE,
                None,
                {"reason": "fewer than 2 mutating actions; no distinct valid route"},
            )
        # Candidate reorderings that keep every action but change execution order.
        candidates = {
            "reversed": list(reversed(actions)),
            "rotate1": actions[1:] + actions[:1],
        }
        for label, reordered in candidates.items():
            try:
                ri = self._grade(task, self._build_trajectory(task, reordered))
                reward = self._reward(ri)
            except Exception:
                reward = None
            if reward == 1.0:
                return ProbeOutcome(
                    "alternative", PASS, reward, {"route": label}
                )
        return ProbeOutcome(
            "alternative",
            NOT_CONSTRUCTIBLE,
            None,
            {"reason": "no tested reordering reached the asserted end state"},
        )

    def probe_policy(self, task: Any, gold: ProbeOutcome) -> ProbeOutcome:
        """Static task/policy/tool/evaluator consistency checks."""
        flags: list[str] = []
        ec = task.evaluation_criteria
        env = self._init_env(task)
        agent_tools = {t.name for t in (env.get_tools() or [])}
        user_tools = set()
        if callable(getattr(env, "get_user_tools", None)):
            user_tools = {t.name for t in (env.get_user_tools() or [])}
        all_tools = agent_tools | user_tools

        # PC1: evaluation criteria present + non-empty reward_basis
        if ec is None or not ec.reward_basis:
            flags.append("no_evaluation_criteria_or_reward_basis")
        # PC2/PC3: reference action tools exist + requestor routing
        missing = []
        misrouted = []
        for a in (ec.actions or []):
            if a.name not in all_tools:
                missing.append(a.name)
            elif a.requestor == "user" and a.name not in user_tools and a.name in agent_tools:
                misrouted.append({"action": a.name, "requestor": "user", "found_in": "agent_tools"})
            elif a.requestor == "assistant" and a.name not in agent_tools and a.name in user_tools:
                misrouted.append({"action": a.name, "requestor": "assistant", "found_in": "user_tools"})
        if missing:
            flags.append(f"reference_action_tool_missing:{missing}")
        if misrouted:
            flags.append(f"reference_action_requestor_misrouted:{misrouted}")
        # PC4: env assertion functions ran (gold produced defined checks / no crash)
        if gold.status == FAIL and "error" in gold.detail:
            flags.append("evaluator_raised_on_gold")
        # PC5: gold reference passes the grader
        if gold.status != PASS:
            flags.append("gold_reference_does_not_pass_grader")

        status = PASS if not flags else FAIL
        return ProbeOutcome("policy", status, None, {"flags": flags,
                                                     "n_agent_tools": len(agent_tools),
                                                     "n_user_tools": len(user_tools)})

    # -- orchestration --------------------------------------------------------
    def _strict_layer(self, task: Any, gold: ProbeOutcome) -> tuple[Optional[float], Optional[bool], Optional[bool], dict]:
        """success_strict = success_official AND sourced semantic checks."""
        M = self._M
        official = gold.reward == 1.0 if gold.reward is not None else None
        conds: dict[str, Any] = {}
        rb = {str(x) for x in task.evaluation_criteria.reward_basis}
        # Condition: all env_assertions met (source: evaluation_criteria.env_assertions)
        if any("ENV_ASSERTION" in x for x in rb):
            ea = gold.detail.get("env_assertions", [])
            conds["all_env_assertions_met"] = {
                "value": all(c["met"] for c in ea) if ea else None,
                "source": "task.evaluation_criteria.env_assertions",
            }
        # Condition: all reference actions matched (source: reward_basis ACTION)
        if any(x.endswith("ACTION") for x in rb):
            ac = gold.detail.get("action_checks", [])
            conds["all_reference_actions_matched"] = {
                "value": all(c["match"] for c in ac) if ac else None,
                "source": "task.evaluation_criteria.actions (reward_basis=ACTION)",
            }
        # Condition: required mutating actions present in the gold trajectory
        conds["required_mutations_present"] = {
            "value": True,  # gold trajectory is built FROM the reference actions
            "source": "reference actions replayed to build gold trajectory",
        }
        strict_checks = [c["value"] for c in conds.values() if c["value"] is not None]
        if official is None:
            success_strict = None
            strict_reward = None
        else:
            success_strict = bool(official and all(strict_checks))
            strict_reward = 1.0 if success_strict else 0.0
        return strict_reward, official, success_strict, conds

    def _is_refusal_task(self, task: Any, env: Any) -> bool:
        """A task whose reference behavior mutates nothing (escalate/refuse).

        Detected structurally: no mutating reference action.  For telecom these
        are the ``transfer_to_human_agents`` escalation tasks whose correct
        end-state equals the (broken) initial state, so ENV_ASSERTION alone is
        satisfied by inaction and the *refusal action itself* must be checked.
        """
        actions = list(task.evaluation_criteria.actions or [])
        if not actions:
            return True
        return not any(self._is_mutating(env, a.name) for a in actions)

    def validate(self, task: Any) -> TaskValidation:
        domain = self.domain
        # hashes
        try:
            t_hash = task_initial_state_hash(task)
            env0 = self._init_env(task)
            e_hash = environment_initial_state_hash(env0, domain=domain)
        except Exception:
            env0 = None
            t_hash, e_hash = None, None

        env_cls = env0 if env0 is not None else self._init_env(task)
        refusal = self._is_refusal_task(task, env_cls)

        gold = self.probe_gold(task)
        noop = self.probe_noop(task)
        omission = self.probe_omission(task)
        alternative = self.probe_alternative(task)
        policy = self.probe_policy(task, gold)
        strict_reward, success_official, success_strict, strict_conds = self._strict_layer(task, gold)

        flags: list[str] = list(policy.detail.get("flags", []))
        rb = {str(x) for x in task.evaluation_criteria.reward_basis}

        # For a refusal task the "alternative route" concept does not apply
        # (there is exactly one correct action: escalate). Report N/A rather
        # than inflating the manual-review queue with structural NOT_CONSTRUCTIBLE.
        if refusal and alternative.status == NOT_CONSTRUCTIBLE:
            alternative = ProbeOutcome(
                "alternative", NA, None,
                {"reason": "refusal/no-action task: escalation is the unique correct action"},
            )

        exclusion = None
        failure = None
        if gold.status != PASS:
            exclusion = GOLD_FAIL
            failure = "gold reference did not achieve reward 1.0"
        elif noop.status != PASS:
            # Applies to normal AND refusal tasks: doing nothing must not pass.
            exclusion = NOOP_FALSE_POSITIVE
            failure = ("no-op trajectory achieved reward 1.0 "
                       "(task passes with no action / refusal not actually checked)")
        elif not refusal and omission.status == NOT_DETECTED:
            exclusion = OMISSION_NOT_DETECTED
            failure = "grader did not detect removal of any single load-bearing action"
        elif policy.status != PASS:
            exclusion = POLICY_MISMATCH
            failure = f"policy/task/grader inconsistency: {flags}"

        # Refusal-specific validity: the escalation must be gated by something
        # the grader checks (ACTION or COMMUNICATE); otherwise inaction passes.
        if refusal:
            flags.append("refusal_task")
            gates_refusal = bool(rb & {"RewardType.ACTION", "RewardType.COMMUNICATE"})
            if not gates_refusal and exclusion is None:
                # noop already caught the concrete case, but flag the structural risk.
                flags.append("refusal_not_gated_by_action_or_communicate")

        admitted = exclusion is None
        # Only NORMAL tasks with a genuinely absent alternate route go to manual
        # review (e.g. single-mutation tasks). Refusal -> alternative=N/A above.
        manual_review = admitted and alternative.status == NOT_CONSTRUCTIBLE
        if manual_review and "alternative_not_constructible" not in flags:
            flags.append("alternative_not_constructible")

        return TaskValidation(
            task_id=str(task.id),
            domain=domain,
            task_class="refusal" if refusal else "normal",
            runtime_commit=self.runtime_commit,
            verified_dataset_commit=self.verified_dataset_commit,
            gold=gold,
            noop=noop,
            omission=omission,
            alternative=alternative,
            policy=policy,
            official_gold_reward=gold.reward,
            strict_gold_reward=strict_reward,
            success_official=success_official,
            success_strict=success_strict,
            strict_conditions=strict_conds,
            task_initial_state_hash=t_hash,
            environment_initial_state_hash=e_hash,
            reward_basis=[str(x) for x in task.evaluation_criteria.reward_basis],
            admitted=admitted,
            exclusion_reason=exclusion,
            manual_review_required=manual_review,
            failure_reason=failure,
            flags=flags,
        )


    def probe_trajectories(self, task: Any) -> dict[str, Any]:
        """Reconstruct probe trajectories as JSON-able artifacts.

        Returns gold / noop / omission / alternative trajectories (best-effort)
        for persistence under artifacts/<task>/<probe>.json.
        """
        from .trajectory import to_jsonable

        actions = list(task.evaluation_criteria.actions or [])
        env = self._init_env(task)
        mut_idx = [i for i, a in enumerate(actions) if self._is_mutating(env, a.name)]
        out: dict[str, Any] = {}
        try:
            out["gold"] = to_jsonable({"trajectory": self._build_trajectory(task, actions)})
        except Exception as exc:
            out["gold"] = {"error": repr(exc)}
        out["noop"] = {"trajectory": []}
        if mut_idx:
            drop = mut_idx[0]
            reduced = [a for j, a in enumerate(actions) if j != drop]
            try:
                out["omission"] = to_jsonable(
                    {"dropped": actions[drop].name, "trajectory": self._build_trajectory(task, reduced)}
                )
            except Exception as exc:
                out["omission"] = {"error": repr(exc)}
        if len(mut_idx) >= 2:
            try:
                out["alternative"] = to_jsonable(
                    {"route": "reversed", "trajectory": self._build_trajectory(task, list(reversed(actions)))}
                )
            except Exception as exc:
                out["alternative"] = {"error": repr(exc)}
        else:
            out["alternative"] = {"note": "NOT_CONSTRUCTIBLE"}
        return out


def outcome_to_dict(o: ProbeOutcome) -> dict[str, Any]:
    return asdict(o)
