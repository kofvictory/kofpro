"""U7 -- validated-slice determinism.

Re-running the validator over the same dataset commit yields the same
admitted task IDs. Uses a small fixed telecom subset for speed.
"""
import pytest

pytest.importorskip("tau2")

from tau2.runner import get_tasks  # noqa: E402

from art_p0.probes import TelecomProbeRunner  # noqa: E402


def _validated(ids, tasks):
    runner = TelecomProbeRunner(
        "telecom", runtime_commit="a2c0247", verified_dataset_commit="864350a"
    )
    out = []
    for tid in ids:
        v = runner.validate(tasks[tid])
        if v.admitted:
            out.append(v.task_id)
    return out


def test_u7_validated_slice_deterministic():
    tasks = {t.id: t for t in get_tasks("telecom")}
    # A small, fixed, diverse subset (first few base-split-style ids present).
    ids = list(tasks)[:8]
    first = _validated(ids, tasks)
    second = _validated(ids, tasks)
    assert first == second
    # Idempotent set identity too.
    assert set(first) == set(second)


def test_u7b_hashes_deterministic_across_runs():
    tasks = {t.id: t for t in get_tasks("telecom")}
    runner = TelecomProbeRunner("telecom")
    tid = next(iter(tasks))
    v1 = runner.validate(tasks[tid])
    v2 = runner.validate(tasks[tid])
    assert v1.environment_initial_state_hash == v2.environment_initial_state_hash
    assert v1.task_initial_state_hash == v2.task_initial_state_hash
    assert v1.admitted == v2.admitted
