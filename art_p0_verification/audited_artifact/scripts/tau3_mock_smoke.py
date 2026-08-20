#!/usr/bin/env python3
"""Run one P0 τ³ mock simulation with auditable instrumentation."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from art_p0.ledger import RunLedger
from art_p0.tau3_runtime import Tau3RunSpec, run_tau3_once
from art_p0.trajectory import TrajectoryStore


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--agent-llm", required=True)
    p.add_argument("--user-llm", required=True)
    p.add_argument("--budget", type=int, required=True)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--task-id", default="create_task_1")
    p.add_argument("--ledger", default="art_runs/p0_mock.jsonl")
    p.add_argument("--trajectories", default="art_runs/trajectories")
    p.add_argument("--max-steps", type=int, default=30)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    artifacts = run_tau3_once(
        Tau3RunSpec(
            agent_llm=args.agent_llm,
            user_llm=args.user_llm,
            tool_budget=args.budget,
            seed=args.seed,
            task_id=args.task_id,
            max_steps=args.max_steps,
        ),
        ledger=RunLedger(Path(args.ledger)),
        trajectory_store=TrajectoryStore(Path(args.trajectories)),
    )
    r = artifacts.record
    print(f"run_id={r.run_id}")
    print(f"harness_hash={r.harness_hash}")
    print(f"tool_calls={r.tool_calls_used}/{r.tool_budget_limit}")
    print(f"budget_exceeded={r.budget_exceeded}")
    print(f"success_official={r.success_official}")
    print(f"termination_reason={r.termination_reason}")
    print(f"trajectory={artifacts.trajectory_path}")
    print(f"ledger={args.ledger}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
