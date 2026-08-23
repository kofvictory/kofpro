#!/usr/bin/env python3
"""Generate all offline P1a artifacts (no API calls).

Produces: manifests/h{0,1,2}.json, p1_task_sample.json, p1_preflight_tasks.json,
p1_budget_table.csv, p1a_design.jsonl (432), preflight_design.jsonl (9).

Deterministic in (SELECTION_SEED, train-validation output, pinned commits).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path


def _quiet():
    os.environ.setdefault("LOGURU_LEVEL", "ERROR")
    try:
        from loguru import logger
        logger.remove(); logger.add(sys.stderr, level="ERROR")
    except Exception:
        pass


def load_eligible(train_audit: Path):
    """Eligible P1a pool = validated train tasks with manual_review == False."""
    elig = []
    for line in open(train_audit):
        r = json.loads(line)
        if r.get("admitted") and not r.get("manual_review_required"):
            elig.append(r["task_id"])
    return elig


def main() -> int:
    _quiet()
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="runs_p1")
    ap.add_argument("--train-audit", default="runs/p1_train_validation/telecom_task_audit.jsonl")
    args = ap.parse_args()
    out = Path(args.out)
    (out / "manifests").mkdir(parents=True, exist_ok=True)
    (out / "trajectories").mkdir(parents=True, exist_ok=True)

    from tau2.registry import registry
    from tau2.runner import get_tasks
    from art_p0 import p1_config as C
    from art_p0.harnesses import build_harness_manifest, HARNESS_IDS
    from art_p0.manifest import ExperimentCondition

    tasks = {t.id: t for t in get_tasks(C.DOMAIN)}

    # --- eligible pool + per-task metadata -----------------------------------
    eligible = load_eligible(Path(args.train_audit))
    meta = []
    for tid in eligible:
        t = tasks[tid]
        meta.append({
            "task_id": tid,
            "family": C.task_family(tid),
            "m_x": C.gold_assistant_tool_calls(t),
        })

    if len(eligible) < 30:
        print(f"STOP: only {len(eligible)} clean train tasks (<30)")
        return 2

    # --- deterministic stratified selection ----------------------------------
    sel = C.stratified_select(meta, seed=C.SELECTION_SEED)
    assert not (set(sel.scientific) & set(sel.preflight))

    # --- manifests (one per harness) -----------------------------------------
    env = registry.get_env_constructor(C.DOMAIN)()
    harness_hashes = {}
    for hid in HARNESS_IDS:
        man = build_harness_manifest(
            env, hid,
            agent_model=C.AGENT_MODEL,
            agent_model_args={"reasoning_effort": C.AGENT_REASONING_EFFORT},
            reasoning_effort=C.AGENT_REASONING_EFFORT,
            user_model=C.USER_MODEL,
            user_model_args={},
            max_steps=C.MAX_STEPS,
            benchmark_runtime_commit=C.RUNTIME_COMMIT,
            verified_dataset_commit=C.VERIFIED_DATASET_COMMIT,
        )
        h = man.manifest_hash()
        harness_hashes[hid] = h
        (out / "manifests" / f"{hid}.json").write_text(
            json.dumps({"harness_id": hid, "manifest": man.to_canonical_dict(),
                        "manifest_hash": h}, indent=2, default=str) + "\n"
        )

    # --- per-task m_x + budgets ----------------------------------------------
    meta_by_id = {m["task_id"]: m for m in meta}

    def budgets_for(tid):
        mx = meta_by_id[tid]["m_x"]
        bl, bm, bh = C.normalized_budgets(mx)
        return mx, {"low": bl, "mid": bm, "high": bh}

    # budget table over scientific + preflight tasks
    with (out / "p1_budget_table.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["task_id", "set", "family", "gold_tool_calls",
                    "budget_low", "budget_mid", "budget_high"])
        for tid in sel.scientific:
            mx, b = budgets_for(tid)
            w.writerow([tid, "scientific", meta_by_id[tid]["family"], mx, b["low"], b["mid"], b["high"]])
        for tid in sel.preflight:
            mx, b = budgets_for(tid)
            w.writerow([tid, "preflight", meta_by_id[tid]["family"], mx, b["low"], b["mid"], b["high"]])

    # --- selection artifacts (with SHA-256 of the complete artifact) ---------
    def strat_info(ids):
        from collections import Counter
        fam = Counter(meta_by_id[i]["family"] for i in ids)
        mxc = Counter(meta_by_id[i]["m_x"] for i in ids)
        return {"by_family": dict(fam), "by_m_x": {str(k): v for k, v in sorted(mxc.items())}}

    sci_art = {
        "purpose": "P1a scientific task sample",
        "domain": C.DOMAIN, "split": C.SPLIT,
        "runtime_commit": C.RUNTIME_COMMIT, "dataset_commit": C.VERIFIED_DATASET_COMMIT,
        "selection_seed": C.SELECTION_SEED,
        "eligible_population_size": len(eligible),
        "eligible_population": sel.eligible,
        "n_selected": len(sel.scientific),
        "stratification": {"keys": ["family", "gold_tool_calls(m_x)"],
                           "selected": strat_info(sel.scientific)},
        "task_ids": sel.scientific,
    }
    sci_art["artifact_sha256"] = C.sha256_of_obj(sci_art)
    (out / "p1_task_sample.json").write_text(json.dumps(sci_art, indent=2) + "\n")

    pre_art = {
        "purpose": "P1a preflight-only tasks (development/calibration; never scientific)",
        "domain": C.DOMAIN, "split": C.SPLIT,
        "runtime_commit": C.RUNTIME_COMMIT, "dataset_commit": C.VERIFIED_DATASET_COMMIT,
        "selection_seed": C.SELECTION_SEED,
        "eligible_population_size": len(eligible),
        "n_selected": len(sel.preflight),
        "disjoint_from_scientific": not (set(sel.preflight) & set(sel.scientific)),
        "stratification": {"selected": strat_info(sel.preflight)},
        "task_ids": sel.preflight,
    }
    pre_art["artifact_sha256"] = C.sha256_of_obj(pre_art)
    (out / "p1_preflight_tasks.json").write_text(json.dumps(pre_art, indent=2) + "\n")

    # --- designs (shared, single implementation in p1_config) ----------------
    bud_map = {tid: budgets_for(tid)[1] for tid in list(sel.scientific) + list(sel.preflight)}
    design_rows = C.build_design_rows(sel.scientific, bud_map, harness_hashes)
    assert len(design_rows) == 432, f"expected 432 rows, got {len(design_rows)}"
    with (out / "p1a_design.jsonl").open("w") as f:
        for r in design_rows:
            f.write(json.dumps(r) + "\n")

    pre_rows = C.build_preflight_rows(sel.preflight, bud_map, harness_hashes)
    assert len(pre_rows) == 9, f"expected 9 preflight rows, got {len(pre_rows)}"
    with (out / "preflight_design.jsonl").open("w") as f:
        for r in pre_rows:
            f.write(json.dumps(r) + "\n")

    summary = {
        "eligible_pool": len(eligible),
        "n_scientific": len(sel.scientific),
        "n_preflight": len(sel.preflight),
        "harness_hashes": harness_hashes,
        "design_rows": len(design_rows),
        "preflight_rows": len(pre_rows),
        "selection_seed": C.SELECTION_SEED,
        "rollout_seeds": list(C.ROLLOUT_SEEDS),
        "preflight_seed": C.PREFLIGHT_SEED,
        "m_x_distribution": strat_info(sel.scientific)["by_m_x"],
        "family_distribution": strat_info(sel.scientific)["by_family"],
    }
    (out / "p1a_build_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
