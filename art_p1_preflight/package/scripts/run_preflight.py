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
        md = rec.get("metadata", {})
        flat = {
            "run_id": r["run_id"], "task_id": r["task_id"], "harness_id": r["harness_id"],
            "budget_limit": rec["tool_budget_limit"],
            "used_tool_calls": rec["tool_calls_used"],
            "budget_exceeded": rec["budget_exceeded"],
            "ceiling_engaged": md.get("ceiling_engaged"),
            "success_strict": rec["success_strict"],
            "success_official": rec["success_official"],
            "input_tokens": rec.get("input_tokens"),
            "output_tokens": rec.get("output_tokens"),
            "tokens": md.get("tokens"),
            "agent_cost": md.get("agent_cost"),
            "user_cost": md.get("user_cost"),
            "total_cost": rec.get("cost_usd"),
            "wall_seconds": rec.get("wall_seconds"),
            "turns": rec.get("turns_used"),
            "termination_reason": rec.get("termination_reason"),
        }
        logs.append(flat)
        print(f"{r['run_id']} {r['harness_id']} B={flat['budget_limit']} "
              f"used={flat['used_tool_calls']} ceiling={flat['ceiling_engaged']} "
              f"strict={flat['success_strict']} official={flat['success_official']} "
              f"overflow={flat['budget_exceeded']} cost={flat['total_cost']} "
              f"wall={flat['wall_seconds']:.1f}s term={flat['termination_reason']}")

    (out / "preflight_runs_table.json").write_text(json.dumps(logs, indent=2, default=str) + "\n")

    # --- ceiling engagement classification --------------------------------
    ceiling = C.summarize_ceiling_engagement(logs)

    # --- cost projection (ACTUAL observed cost preferred) -----------------
    costs = [x["total_cost"] for x in logs if x.get("total_cost") is not None]
    agent_costs = [x["agent_cost"] for x in logs if x.get("agent_cost") is not None]
    user_costs = [x["user_cost"] for x in logs if x.get("user_cost") is not None]
    walls = [x["wall_seconds"] for x in logs if x.get("wall_seconds") is not None]
    by_harness = {}
    for hid in ("h0", "h1", "h2"):
        sub = [x for x in logs if x["harness_id"] == hid]
        tin = [x["input_tokens"] for x in sub if x.get("input_tokens") is not None]
        tout = [x["output_tokens"] for x in sub if x.get("output_tokens") is not None]
        by_harness[hid] = {
            "n": len(sub),
            "mean_input_tokens": (sum(tin) / len(tin)) if tin else None,
            "mean_output_tokens": (sum(tout) / len(tout)) if tout else None,
            "mean_wall_seconds": (sum(x["wall_seconds"] for x in sub) / len(sub)) if sub else None,
        }

    summary = {"n_runs": len(logs), "ceiling_engagement": ceiling, "by_harness": by_harness}
    if costs:
        c_run = sum(costs) / len(costs)
        summary.update({
            "cost_source": "observed_provider_cost",
            "mean_cost_per_run": c_run,
            "median_cost_per_run": statistics.median(costs),
            "min_cost_per_run": min(costs), "max_cost_per_run": max(costs),
            "mean_agent_cost": (sum(agent_costs) / len(agent_costs)) if agent_costs else None,
            "mean_user_cost": (sum(user_costs) / len(user_costs)) if user_costs else None,
            "mean_wall_seconds": (sum(walls) / len(walls)) if walls else None,
            "C_432_projected": 432 * c_run,
            "C_432_with_20pct_margin": 1.2 * 432 * c_run,
        })
    else:
        summary["cost_source"] = "UNAVAILABLE"
        summary["note"] = (
            "no provider cost metadata returned; reconstruct from observed token "
            "usage x pinned model pricing and label the result RECONSTRUCTED"
        )
    (out / "preflight_cost_summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print("\n=== CEILING ENGAGEMENT: " + ceiling["verdict"] + " ===")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
