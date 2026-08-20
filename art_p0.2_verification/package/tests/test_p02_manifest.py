"""U3, U4 -- FrozenHarnessManifest stability and sensitivity.

These tests are pure-Python (no tau2 needed).
"""
from art_p0.manifest import ExperimentCondition, FrozenHarnessManifest


def _manifest(**over):
    base = dict(
        agent_model="frontier/x",
        agent_model_args={"temperature": 0.0},
        agent_system_prompt="SYSTEM PROMPT v1",
        agent_policy_prompt="POLICY TEXT v1",
        domain_policy_text="DOMAIN POLICY v1",
        tool_schema=[{"name": "a", "params": {}}],
        tool_permissions={"a": "read"},
        user_model="user/y",
        max_steps=100,
        benchmark_runtime_commit="a2c0247",
        verified_dataset_commit="864350a",
    )
    base.update(over)
    return FrozenHarnessManifest.from_texts(**base)


def test_u3_budget_change_same_harness_hash():
    """U3: varying only the resource budget keeps the harness hash constant.

    Budget lives in ExperimentCondition, never in the manifest.
    """
    m = _manifest()
    h = m.manifest_hash()
    c1 = ExperimentCondition(harness_hash=h, task_id="t1", seed=42, resource_budget=1)
    c2 = ExperimentCondition(harness_hash=h, task_id="t1", seed=42, resource_budget=4)
    # Same apparatus identity across budgets ...
    assert c1.harness_hash == c2.harness_hash == h
    # ... but different experimental-condition identity.
    assert c1.condition_hash() != c2.condition_hash()


def test_u3b_seed_and_task_not_in_harness_identity():
    """seed/task_id also do not affect harness identity."""
    m = _manifest()
    h = m.manifest_hash()
    a = ExperimentCondition(harness_hash=h, task_id="t1", seed=1, resource_budget=2)
    b = ExperimentCondition(harness_hash=h, task_id="t2", seed=2, resource_budget=2)
    assert a.harness_hash == b.harness_hash == h
    assert a.condition_hash() != b.condition_hash()


def test_u4_system_prompt_change_different_hash():
    """U4: changing the system prompt changes the harness hash."""
    assert _manifest().manifest_hash() != _manifest(
        agent_system_prompt="SYSTEM PROMPT v2"
    ).manifest_hash()


def test_u4b_domain_policy_change_different_hash():
    """U4: changing the domain policy text changes the harness hash."""
    assert _manifest().manifest_hash() != _manifest(
        domain_policy_text="DOMAIN POLICY v2"
    ).manifest_hash()


def test_u4c_model_and_commit_change_different_hash():
    assert _manifest().manifest_hash() != _manifest(agent_model="frontier/z").manifest_hash()
    assert _manifest().manifest_hash() != _manifest(
        benchmark_runtime_commit="deadbeef"
    ).manifest_hash()
    assert _manifest().manifest_hash() != _manifest(
        tool_permissions={"a": "write"}
    ).manifest_hash()


def test_manifest_hash_deterministic():
    assert _manifest().manifest_hash() == _manifest().manifest_hash()
    assert len(_manifest().manifest_hash()) == 64
