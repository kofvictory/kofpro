"""U5, U6 -- probe detection power (no-op false positive; omission).

Uses the lightweight mock domain with synthetic evaluation criteria so the
tests are fast and deterministic. Skipped if tau2 is absent.
"""
import pytest

pytest.importorskip("tau2")

from tau2.data_model.tasks import Task  # noqa: E402
from tau2.runner import get_tasks  # noqa: E402

from art_p0.probes import DETECTED, FAIL, PASS, TelecomProbeRunner  # noqa: E402


def _mock_tasks():
    return {t.id: t for t in get_tasks("mock")}


def test_u5_noop_false_positive_is_detected():
    """U5: a task whose assertion already holds at init must be caught as a
    no-op false positive (probe_noop -> FAIL)."""
    base = _mock_tasks()["create_task_1_with_env_assertions"]
    d = base.model_dump()
    d["id"] = "synthetic_noop_fp"
    # Assertion true at init (user_1 already has exactly 1 task), no action needed.
    d["evaluation_criteria"]["actions"] = []
    d["evaluation_criteria"]["env_assertions"] = [
        {
            "env_type": "assistant",
            "func_name": "assert_number_of_tasks",
            "arguments": {"user_id": "user_1", "expected_number": 1},
            "assert_value": True,
            "message": None,
        }
    ]
    d["evaluation_criteria"]["reward_basis"] = ["ENV_ASSERTION"]
    degenerate = Task.model_validate(d)

    runner = TelecomProbeRunner("mock")
    out = runner.probe_noop(degenerate)
    assert out.reward == 1.0
    assert out.status == FAIL  # no-op wrongly passes -> flagged

    # And the full validator excludes it as NOOP_FALSE_POSITIVE.
    v = runner.validate(degenerate)
    assert not v.admitted
    assert v.exclusion_reason == "NOOP_FALSE_POSITIVE"


def test_u5b_state_changing_task_noop_correctly_fails():
    """Control: a genuine state-changing task must NOT pass under no-op."""
    task = _mock_tasks()["create_task_1"]
    runner = TelecomProbeRunner("mock")
    out = runner.probe_noop(task)
    assert out.reward != 1.0
    assert out.status == PASS


def test_u6_omission_detected_on_required_mutation():
    """U6: dropping the required mutation must be detected as failure."""
    task = _mock_tasks()["create_task_1"]  # requires create_task
    runner = TelecomProbeRunner("mock")
    gold = runner.probe_gold(task)
    assert gold.status == PASS and gold.reward == 1.0
    omission = runner.probe_omission(task)
    assert omission.status == DETECTED
    assert "create_task" in omission.detail["load_bearing_actions"]
