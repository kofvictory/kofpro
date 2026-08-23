from art_p0.validator import ProbeResult, TaskValidator


def ok(name):
    return lambda task: ProbeResult(True, name=name, evidence={"task": task["id"]})


def test_validator_accepts_only_all_passing_probes():
    validator = TaskValidator(
        get_task_id=lambda t: t["id"],
        gold_probe=ok("gold"),
        noop_probe=ok("noop"),
        omission_probe=ok("omission"),
        alternative_probe=ok("alternative"),
        policy_probe=ok("policy"),
    )
    result = validator.validate({"id": "x"})
    assert result.accepted


def test_validator_rejects_one_failed_probe():
    validator = TaskValidator(
        get_task_id=lambda t: t["id"],
        gold_probe=ok("gold"),
        noop_probe=lambda t: ProbeResult(False, name="noop", details="no-op passed unexpectedly"),
        omission_probe=ok("omission"),
        alternative_probe=ok("alternative"),
        policy_probe=ok("policy"),
    )
    result = validator.validate({"id": "x"})
    assert not result.accepted
