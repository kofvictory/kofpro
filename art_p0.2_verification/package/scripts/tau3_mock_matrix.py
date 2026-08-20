#!/usr/bin/env python3
"""Run the P0 mock matrix at budgets 1/2/4 and check scientific invariants."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from art_p0.ledger import RunLedger
from art_p0.tau3_runtime import Tau3RunSpec, check_matrix_invariants, run_tau3_once
from art_p0.trajectory import TrajectoryStore


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--agent-llm", required=True)
    p.add_argument("--user-llm", required=True)
    p.add_argument("--budgets", type=int, nargs="+", default=[1, 2, 4])
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--task-id", default="create_task_1")
    p.add_argument("--ledger", default="art_runs/p0_mock_matrix.jsonl")
    p.add_argument("--trajectories", default="art_runs/trajectories")
    p.add_argument("--max-steps", type=int, default=30)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    ledger = RunLedger(Path(args.ledger))
    store = TrajectoryStore(Path(args.trajectories))
    records = []
    for budget in args.budgets:
        art = run_tau3_once(
            Tau3RunSpec(
                agent_llm=args.agent_llm,
                user_llm=args.user_llm,
                tool_budget=budget,
                seed=args.seed,
                task_id=args.task_id,
                max_steps=args.max_steps,
            ),
            ledger=ledger,
            trajectory_store=store,
        )
        records.append(art.record)
        print(
            f"B={budget}: used={art.record.tool_calls_used}, "
            f"overflow={art.record.budget_exceeded}, "
            f"success={art.record.success_official}"
        )

    errors = check_matrix_invariants(records)
    if errors:
        print("P0_MATRIX=FAIL")
        for err in errors:
            print(f"- {err}")
        return 2
    print("P0_MATRIX=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
