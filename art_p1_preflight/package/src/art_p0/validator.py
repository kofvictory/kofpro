from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol


class Probe(Protocol):
    def __call__(self, task: Any) -> "ProbeResult": ...


@dataclass(frozen=True)
class ProbeResult:
    passed: bool
    name: str
    details: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TaskValidationResult:
    task_id: str
    gold: ProbeResult
    noop: ProbeResult
    omission: ProbeResult
    alternative: ProbeResult
    policy: ProbeResult
    refusal_task: bool = False

    @property
    def accepted(self) -> bool:
        # Probe semantics: each .passed means the desired validation property held.
        # For a normal task, noop must demonstrate that no-op is rejected.
        # Refusal/no-action tasks may use a custom noop probe that checks required
        # communication rather than state mutation.
        return all(
            p.passed
            for p in (self.gold, self.noop, self.omission, self.alternative, self.policy)
        )


class TaskValidator:
    """Composable five-probe task-validity audit.

    The validator deliberately does not know tau-bench internals. Each probe can
    replay a trajectory, call a benchmark evaluator, or perform a static policy
    consistency check. This keeps the scientific acceptance rule stable while
    adapters evolve.
    """

    def __init__(
        self,
        *,
        get_task_id: Callable[[Any], str],
        gold_probe: Probe,
        noop_probe: Probe,
        omission_probe: Probe,
        alternative_probe: Probe,
        policy_probe: Probe,
        is_refusal_task: Optional[Callable[[Any], bool]] = None,
    ) -> None:
        self.get_task_id = get_task_id
        self.gold_probe = gold_probe
        self.noop_probe = noop_probe
        self.omission_probe = omission_probe
        self.alternative_probe = alternative_probe
        self.policy_probe = policy_probe
        self.is_refusal_task = is_refusal_task or (lambda _: False)

    def validate(self, task: Any) -> TaskValidationResult:
        return TaskValidationResult(
            task_id=self.get_task_id(task),
            gold=self.gold_probe(task),
            noop=self.noop_probe(task),
            omission=self.omission_probe(task),
            alternative=self.alternative_probe(task),
            policy=self.policy_probe(task),
            refusal_task=self.is_refusal_task(task),
        )
