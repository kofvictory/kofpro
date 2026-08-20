#!/usr/bin/env python3
"""Offline audit of one or more P0 JSONL ledgers."""
from __future__ import annotations

import argparse
from collections import defaultdict

from art_p0.ledger import RunLedger


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("ledger")
    args = p.parse_args()
    rows = RunLedger(args.ledger).read_all()
    if not rows:
        raise SystemExit("ledger is empty")

    failures: list[str] = []
    by_key = defaultdict(list)
    for r in rows:
        if r.tool_calls_used > r.tool_budget_limit:
            failures.append(f"{r.run_id}: used {r.tool_calls_used} > limit {r.tool_budget_limit}")
        if not r.harness_hash or len(r.harness_hash) != 64:
            failures.append(f"{r.run_id}: invalid harness hash")
        by_key[(r.task_id, r.harness_hash, r.seed)].append(r)

    # Nested-budget structural check: lower-budget observed usage must never exceed its own limit.
    # This does not assert identical trajectories across budgets; that requires trajectory hashes
    # and is intentionally deferred to P0 integration.
    for key, group in by_key.items():
        group.sort(key=lambda r: r.tool_budget_limit)
        for r in group:
            if r.tool_calls_used > r.tool_budget_limit:
                failures.append(f"{key}: budget invariant failed")

    print(f"records={len(rows)}")
    print(f"failures={len(failures)}")
    for f in failures:
        print(f"FAIL: {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
