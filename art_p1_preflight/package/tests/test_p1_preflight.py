"""P1-U1 .. P1-U12 -- P1a preflight design/config verification (no API calls).

Artifact-dependent checks resolve the build output directory produced by
`scripts/build_p1a.py`; manifest/formula/strict checks are self-contained.
"""
import json
import os
from pathlib import Path

import pytest

pytest.importorskip("tau2")

from tau2.registry import registry  # noqa: E402
from tau2.runner import get_tasks  # noqa: E402

from art_p0 import p1_config as C  # noqa: E402
from art_p0.harnesses import HARNESS_IDS, build_harness_manifest  # noqa: E402

PINS = (C.RUNTIME_COMMIT, C.VERIFIED_DATASET_COMMIT)


def _find_artifacts() -> Path:
    cands = []
    if os.environ.get("ART_P1_DIR"):
        cands.append(Path(os.environ["ART_P1_DIR"]))
    here = Path(__file__).resolve()
    for base in [Path.cwd(), *here.parents]:
        cands.append(base / "runs_p1")
    for c in cands:
        if (c / "p1a_design.jsonl").exists():
            return c
    pytest.skip("P1a build artifacts (runs_p1/) not found; run scripts/build_p1a.py")


@pytest.fixture(scope="module")
def art():
    return _find_artifacts()


@pytest.fixture(scope="module")
def tau_env():
    return registry.get_env_constructor(C.DOMAIN)()


@pytest.fixture(scope="module")
def manifests(tau_env):
    out = {}
    for hid in HARNESS_IDS:
        out[hid] = build_harness_manifest(
            tau_env, hid,
            agent_model=C.AGENT_MODEL,
            agent_model_args={"reasoning_effort": C.AGENT_REASONING_EFFORT},
            reasoning_effort=C.AGENT_REASONING_EFFORT,
            user_model=C.USER_MODEL, user_model_args={},
            max_steps=C.MAX_STEPS,
            benchmark_runtime_commit=C.RUNTIME_COMMIT,
            verified_dataset_commit=C.VERIFIED_DATASET_COMMIT,
        )
    return out


# ---------------------------------------------------------------------------
def test_p1_u1_same_harness_diff_budget_same_hash(manifests):
    """P1-U1: same harness + different budget -> same harness hash."""
    h = manifests["h0"].manifest_hash()
    from art_p0.manifest import ExperimentCondition
    c_low = ExperimentCondition(h, "task", 1000, 1)
    c_high = ExperimentCondition(h, "task", 1000, 4)
    assert c_low.harness_hash == c_high.harness_hash == h
    assert c_low.condition_hash() != c_high.condition_hash()


def test_p1_u2_diff_harness_prompt_diff_hash(manifests):
    """P1-U2: different harness prompt/policy -> different harness hash."""
    hashes = {hid: manifests[hid].manifest_hash() for hid in HARNESS_IDS}
    assert len(set(hashes.values())) == 3, hashes


def test_p1_u3_sample_deterministic(art):
    """P1-U3: task selection is deterministic given eligible pool + seed."""
    sample = json.load(open(art / "p1_task_sample.json"))
    eligible = sample["eligible_population"]
    tasks = {t.id: t for t in get_tasks(C.DOMAIN)}
    meta = [{"task_id": t, "family": C.task_family(t),
             "m_x": C.gold_assistant_tool_calls(tasks[t])} for t in eligible]
    s1 = C.stratified_select(meta, seed=C.SELECTION_SEED)
    s2 = C.stratified_select(meta, seed=C.SELECTION_SEED)
    assert s1.scientific == s2.scientific == sample["task_ids"]
    assert s1.preflight == s2.preflight


def test_p1_u4_preflight_scientific_disjoint(art):
    """P1-U4: preflight and scientific sets are disjoint."""
    sci = set(json.load(open(art / "p1_task_sample.json"))["task_ids"])
    pre = set(json.load(open(art / "p1_preflight_tasks.json"))["task_ids"])
    assert sci and pre
    assert not (sci & pre)


def test_p1_u5_no_test_split_task_anywhere(art):
    """P1-U5: no held-out test-split task appears anywhere."""
    splits = json.load(open(_split_path()))
    test_ids = set(splits["test"])
    sci = set(json.load(open(art / "p1_task_sample.json"))["task_ids"])
    pre = set(json.load(open(art / "p1_preflight_tasks.json"))["task_ids"])
    elig = set(json.load(open(art / "p1_task_sample.json"))["eligible_population"])
    assert not (sci & test_ids)
    assert not (pre & test_ids)
    assert not (elig & test_ids)


@pytest.mark.parametrize("m_x,expected", [
    (0, (1, 2, 3)),
    (1, (1, 2, 3)),
    (2, (2, 3, 4)),
    (3, (3, 5, 6)),
    (4, (4, 6, 8)),
    (10, (10, 15, 20)),
])
def test_p1_u6_budget_formula(m_x, expected):
    """P1-U6: budget normalization matches the specified formula exactly."""
    assert C.normalized_budgets(m_x) == expected
    bl, bm, bh = expected
    assert 1 <= bl < bm < bh


def test_p1_u7_432_scientific_rows(art):
    """P1-U7: exactly 432 scientific design rows."""
    rows = [json.loads(l) for l in open(art / "p1a_design.jsonl")]
    assert len(rows) == 432
    # also reconstruct in-memory and confirm 432
    sample = json.load(open(art / "p1_task_sample.json"))
    tasks = {t.id: t for t in get_tasks(C.DOMAIN)}
    bud = C.budgets_by_task(sample["task_ids"], tasks)
    hh = {hid: json.load(open(art / "manifests" / f"{hid}.json"))["manifest_hash"] for hid in HARNESS_IDS}
    assert len(C.build_design_rows(sample["task_ids"], bud, hh)) == 432


def test_p1_u8_9_preflight_rows(art):
    """P1-U8: exactly 9 preflight rows."""
    rows = [json.loads(l) for l in open(art / "preflight_design.jsonl")]
    assert len(rows) == 9
    assert {r["budget_level"] for r in rows} == {"mid"}
    assert {r["rollout_seed"] for r in rows} == {C.PREFLIGHT_SEED}


def test_p1_u9_two_replicate_seeds_per_condition(art):
    """P1-U9: every scientific (task,harness,budget) has 2 distinct seeds."""
    rows = [json.loads(l) for l in open(art / "p1a_design.jsonl")]
    from collections import defaultdict
    seeds = defaultdict(set)
    for r in rows:
        seeds[(r["task_id"], r["harness_id"], r["budget_level"])].add(r["rollout_seed"])
    assert len(seeds) == 24 * 3 * 3
    assert all(s == set(C.ROLLOUT_SEEDS) for s in seeds.values())


def test_p1_u10_selected_in_validated_train(art):
    """P1-U10: every selected task belongs to D_validated_train (eligible)."""
    sample = json.load(open(art / "p1_task_sample.json"))
    elig = set(sample["eligible_population"])
    pre = json.load(open(art / "p1_preflight_tasks.json"))["task_ids"]
    assert set(sample["task_ids"]) <= elig
    assert set(pre) <= elig


def test_p1_u11_commits_match_pins(art, manifests):
    """P1-U11: runtime/dataset commits in every manifest and design row match pins."""
    for hid in HARNESS_IDS:
        m = json.load(open(art / "manifests" / f"{hid}.json"))["manifest"]
        assert m["benchmark_runtime_commit"] == C.RUNTIME_COMMIT
        assert m["verified_dataset_commit"] == C.VERIFIED_DATASET_COMMIT
        assert manifests[hid].benchmark_runtime_commit == C.RUNTIME_COMMIT
    for path in ("p1a_design.jsonl", "preflight_design.jsonl"):
        for line in open(art / path):
            r = json.loads(line)
            assert (r["runtime_commit"], r["dataset_commit"]) == PINS


def test_p1_u12_budget_overflow_forces_failure():
    """P1-U12: budget overflow => scientific success_strict is False."""
    assert C.scientific_success_strict(True, True) is False
    assert C.scientific_success_strict(False, True) is False
    assert C.scientific_success_strict(True, False) is True
    assert C.scientific_success_strict(False, False) is False
    assert C.scientific_success_strict(None, False) is None


def test_p1_u13_preflight_spans_mx_levels(art):
    """P1-U13: preflight tasks span distinct m_x levels (v2 re-selection).

    v1 preflight was all m_x==1, exercising a single point of the resource
    interface. v2 must cover the distinct m_x levels available in the pool.
    """
    d = json.load(open(art / "p1_preflight_tasks.json"))
    tasks = {t.id: t for t in get_tasks(C.DOMAIN)}
    mxs = [C.gold_assistant_tool_calls(tasks[t]) for t in d["task_ids"]]
    assert len(set(mxs)) == len(d["task_ids"]) == C.N_PREFLIGHT, mxs
    assert set(mxs) == {0, 1, 2}, mxs
    fams = [C.task_family(t) for t in d["task_ids"]]
    assert len(set(fams)) == 3, fams  # families maximally spread


def test_p1_u13b_preflight_selection_deterministic(art):
    """v2 preflight selection is deterministic given (pool, seed)."""
    sample = json.load(open(art / "p1_task_sample.json"))
    sci = set(sample["task_ids"])
    tasks = {t.id: t for t in get_tasks(C.DOMAIN)}
    pool = [{"task_id": t, "family": C.task_family(t),
             "m_x": C.gold_assistant_tool_calls(tasks[t])}
            for t in sample["eligible_population"] if t not in sci]
    a = C.select_preflight_by_mx(pool, seed=C.PREFLIGHT_SELECTION_SEED)
    b = C.select_preflight_by_mx(pool, seed=C.PREFLIGHT_SELECTION_SEED)
    assert a == b == json.load(open(art / "p1_preflight_tasks.json"))["task_ids"]
    assert not (set(a) & sci)


def test_p1_u14_ceiling_engaged_semantics():
    """P1-U14: ceiling_engaged = (used == B) OR budget_exceeded."""
    assert C.ceiling_engaged(2, 2, False) is True     # exactly at ceiling
    assert C.ceiling_engaged(1, 2, False) is False    # below ceiling
    assert C.ceiling_engaged(0, 3, False) is False
    assert C.ceiling_engaged(1, 2, True) is True      # overflow, any usage
    assert C.ceiling_engaged(3, 3, True) is True


def test_p1_u14b_ceiling_summary_thresholds():
    """GREEN/YELLOW/RED classification thresholds."""
    def rec(task, eng):
        return {"task_id": task, "ceiling_engaged": eng}
    none_ = [rec(f"t{i}", False) for i in range(9)]
    assert C.summarize_ceiling_engagement(none_)["verdict"] == "RED"
    one = none_[:8] + [rec("tA", True)]
    assert C.summarize_ceiling_engagement(one)["verdict"] == "YELLOW"
    two = none_[:7] + [rec("tA", True), rec("tB", True)]
    assert C.summarize_ceiling_engagement(two)["verdict"] == "YELLOW"
    green = none_[:6] + [rec("tA", True), rec("tA", True), rec("tB", True)]
    assert C.summarize_ceiling_engagement(green)["verdict"] == "GREEN"
    # >=3 engaged but all on ONE task -> not GREEN (diversity requirement)
    concentrated = none_[:6] + [rec("tA", True)] * 3
    assert C.summarize_ceiling_engagement(concentrated)["verdict"] == "YELLOW"


def test_p1_u15_scientific_sample_unchanged(art):
    """The frozen 24-task scientific sample must not move when preflight is
    re-selected: seed and artifact hash are self-consistent."""
    sample = json.load(open(art / "p1_task_sample.json"))
    assert sample["selection_seed"] == C.SELECTION_SEED
    assert len(sample["task_ids"]) == C.N_SCIENTIFIC
    body = {k: v for k, v in sample.items() if k != "artifact_sha256"}
    assert C.sha256_of_obj(body) == sample["artifact_sha256"]


def _split_path() -> Path:
    here = Path(__file__).resolve()
    for base in [Path.cwd(), *here.parents]:
        p = base / "tau2-bench" / "data" / "tau2" / "domains" / C.DOMAIN / "split_tasks.json"
        if p.exists():
            return p
    from tau2.utils import DATA_DIR  # type: ignore
    return Path(DATA_DIR) / "tau2" / "domains" / C.DOMAIN / "split_tasks.json"
