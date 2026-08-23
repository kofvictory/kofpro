#!/usr/bin/env python3
"""Execute the 9 P1 preflight rollouts -- ONLY if API credentials are present.

Hard rules:
  * Never prints/logs/requests secret keys.
  * If credentials are absent -> print "P1 PREFLIGHT READY -- API CREDENTIALS
    NOT PRESENT" and exit 0 WITHOUT any API call. Never fabricate mock results.
  * Runs exactly the 9 rows in preflight_design.jsonl. Never touches
    p1a_design.jsonl (the 432 scientific rows).
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

CRED_KEYS = (
    "OPENAI_API_KEY", "AZURE_API_KEY", "AZURE_OPENAI_API_KEY",
    "OPENROUTER_API_KEY", "LITELLM_API_KEY",
)


def credentials_present() -> bool:
    return any(os.environ.get(k) for k in CRED_KEYS)


def _quiet():
    os.environ.setdefault("LOGURU_LEVEL", "ERROR")
    try:
        from loguru import logger
        logger.remove(); logger.add(sys.stderr, level="ERROR")
    except Exception:
        pass


def main() -> int:
    _quiet()
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", default="runs_p1/preflight_design.jsonl")
    ap.add_argument("--out", default="runs_p1")
    args = ap.parse_args()
    out = Path(args.out)
    (out / "trajectories").mkdir(parents=True, exist_ok=True)

    rows = [json.loads(l) for l in open(args.design)]
    assert len(rows) == 9, f"preflight design must have 9 rows, got {len(rows)}"
    # Safety: refuse to run anything that is not a preflight row.
    assert all(r["run_id"].startswith("pf_") for r in rows), "non-preflight row detected"

    if not credentials_present():
        print("P1 PREFLIGHT READY — API CREDENTIALS NOT PRESENT")
        print(f"(9 preflight rows staged in {args.design}; not executed)")
        return 0

    from art_p0.ledger import RunLedger
    from art_p0.trajectory import TrajectoryStore
    from art_p0.p1_rollout import P1RolloutSpec, run_p1_rollout
    from art_p0 import p1_config as C

    ledger = RunLedger(out / "p1_preflight.jsonl")
    store = TrajectoryStore(out / "trajectories")
    logs = []
    for r in rows:
        spec = P1RolloutSpec(
            task_id=r["task_id"], harness_id=r["harness_id"],
            harness_hash=r["harness_hash"], condition_hash=r["condition_hash"],
            budget_level=r["budget_level"], tool_budget_limit=r["tool_budget_limit"],
            rollout_seed=r["rollout_seed"], agent_model=r["agent_model"],
            user_model=r["user_model"], reasoning_effort=r["reasoning_effort"],
            runtime_commit=r["runtime_commit"], dataset_commit=r["dataset_commit"],
            domain=C.DOMAIN, max_steps=C.MAX_STEPS,
            agent_model_args={}, user_model_args={},
        )
        rec = run_p1_rollout(spec, ledger=ledger, trajectory_store=store, run_id=r["run_id"])
        logs.append(rec)
        print(f"{r['run_id']} {r['harness_id']} used={rec['tool_calls_used']}/{rec['tool_budget_limit']} "
              f"strict={rec['success_strict']} official={rec['success_official']} "
              f"overflow={rec['budget_exceeded']} cost={rec.get('cost_usd')}")

    # cost projection (from ACTUAL observed cost; reconstructed only if missing)
    costs = [x.get("cost_usd") for x in logs if x.get("cost_usd") is not None]
    summary = {"n_runs": len(logs)}
    if costs:
        c_run = sum(costs) / len(costs)
        summary.update({
            "mean_cost_per_run": c_run,
            "median_cost_per_run": statistics.median(costs),
            "min_cost": min(costs), "max_cost": max(costs),
            "C_432": 432 * c_run,
            "C_safe_1.2x": 1.2 * 432 * c_run,
            "cost_source": "observed_provider_cost",
        })
    else:
        summary["note"] = "no provider cost metadata; reconstruct from tokens x pinned pricing"
    (out / "preflight_cost_summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
