#!/usr/bin/env python3
"""P0.2 Telecom TaskValidator pipeline -> D_validated (no LLM).

Runs the five-probe validator over a Telecom split using the real, pinned tau2
evaluator and writes the machine-readable audit artifacts:

  <out>/telecom_task_audit.jsonl          # one TaskValidation row per task
  <out>/telecom_task_audit.csv            # flat table
  <out>/validated_telecom_task_ids.json   # the admitted slice (D_validated)
  <out>/excluded_telecom_tasks.jsonl      # excluded tasks + reason codes
  <out>/artifacts/<task>/{gold,noop,omission,alternative}.json
  <out>/frozen_harness_manifest.json      # example FrozenHarnessManifest + hash
  <out>/summary.json

Determinism: the validated slice depends only on (runtime_commit,
verified_dataset_commit, split); re-running yields identical IDs (U7).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path


def _quiet_logging():
    os.environ.setdefault("LOGURU_LEVEL", "ERROR")
    try:
        from loguru import logger

        logger.remove()
        logger.add(sys.stderr, level="ERROR")
    except Exception:
        pass


def _safe(task_id: str) -> str:
    import hashlib

    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", task_id)[:100]
    # Append a short stable hash so long IDs that truncate to the same slug
    # still get distinct artifact directories.
    digest = hashlib.sha256(task_id.encode("utf-8")).hexdigest()[:10]
    return f"{slug}__{digest}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--domain", default="telecom")
    p.add_argument("--split", default="base",
                   help="telecom split: base/small/train/test/full")
    p.add_argument("--runtime-commit", default="a2c024725189473d2d7cea3a5cfdbcc67478e41f")
    p.add_argument("--verified-commit", default="864350a8971a8f8ee9e7b8472e2edc380a806b0c")
    p.add_argument("--out", default="runs_p02")
    p.add_argument("--limit", type=int, default=0, help="0 = all tasks in split")
    p.add_argument("--no-artifacts", action="store_true")
    return p.parse_args()


def main() -> int:
    _quiet_logging()
    args = parse_args()
    out = Path(args.out)
    (out / "artifacts").mkdir(parents=True, exist_ok=True)

    from tau2.runner import get_tasks
    from tau2.registry import registry
    from art_p0.probes import TelecomProbeRunner
    from art_p0.manifest import build_manifest_from_tau2_env

    # Load split ids
    tasks = get_tasks(args.domain)
    byid = {t.id: t for t in tasks}
    split_path = Path("tau2-bench/data/tau2/domains") / args.domain / "split_tasks.json"
    if not split_path.exists():
        # fall back to installed data dir
        from tau2.utils import DATA_DIR  # type: ignore
        split_path = Path(DATA_DIR) / "tau2" / "domains" / args.domain / "split_tasks.json"
    splits = json.load(open(split_path))
    ids = splits[args.split]
    if args.limit:
        ids = ids[: args.limit]

    runner = TelecomProbeRunner(
        args.domain,
        runtime_commit=args.runtime_commit,
        verified_dataset_commit=args.verified_commit,
    )

    # Example frozen harness manifest (apparatus identity for the rollout stage).
    env0 = registry.get_env_constructor(args.domain)()
    manifest = build_manifest_from_tau2_env(
        env0,
        agent_model="<frontier-model-TBD>",
        agent_system_prompt="<agent system prompt frozen at rollout>",
        agent_policy_prompt=env0.get_policy() if callable(getattr(env0, "get_policy", None)) else None,
        user_model="<user-sim-model-TBD>",
        max_steps=100,
        benchmark_runtime_commit=args.runtime_commit,
        verified_dataset_commit=args.verified_commit,
        extra={"domain": args.domain, "evaluation_type": "ALL"},
    )
    (out / "frozen_harness_manifest.json").write_text(
        json.dumps({"manifest": manifest.to_canonical_dict(),
                    "manifest_hash": manifest.manifest_hash()}, indent=2, default=str) + "\n"
    )

    rows = []
    validations = []
    audit_f = (out / "telecom_task_audit.jsonl").open("w", encoding="utf-8")
    excl_f = (out / "excluded_telecom_tasks.jsonl").open("w", encoding="utf-8")
    n = len(ids)
    for k, tid in enumerate(ids, 1):
        t = byid.get(tid)
        if t is None:
            excl_f.write(json.dumps({"task_id": tid, "exclusion_reason": "NOT_FOUND_IN_RUNTIME"}) + "\n")
            continue
        v = runner.validate(t)
        validations.append(v)
        row = v.to_row()
        rows.append(row)
        # full record (with probe details) to jsonl
        from dataclasses import asdict
        rec = asdict(v)
        audit_f.write(json.dumps(rec, default=str) + "\n")
        if not v.admitted:
            excl_f.write(json.dumps({
                "task_id": v.task_id,
                "exclusion_reason": v.exclusion_reason,
                "failure_reason": v.failure_reason,
                "flags": v.flags,
            }, default=str) + "\n")
        # artifacts
        if not args.no_artifacts:
            try:
                traj = runner.probe_trajectories(t)
                adir = out / "artifacts" / _safe(tid)
                adir.mkdir(parents=True, exist_ok=True)
                for name, payload in traj.items():
                    (adir / f"{name}.json").write_text(
                        json.dumps(payload, indent=2, default=str) + "\n"
                    )
            except Exception as exc:
                excl_f.write(json.dumps({"task_id": tid, "artifact_error": repr(exc)}) + "\n")
        if k % 10 == 0 or k == n:
            print(f"[{k}/{n}] validated", flush=True)
    audit_f.close()
    excl_f.close()

    # CSV
    csv_path = out / "telecom_task_audit.csv"
    if rows:
        keys = list(rows[0].keys())
        with csv_path.open("w", newline="", encoding="utf-8") as cf:
            w = csv.DictWriter(cf, fieldnames=keys)
            w.writeheader()
            for r in rows:
                w.writerow({k: (json.dumps(vv) if isinstance(vv, (list, dict)) else vv) for k, vv in r.items()})

    validated_ids = [v.task_id for v in validations if v.admitted]
    excluded = [v for v in validations if not v.admitted]
    manual = [v.task_id for v in validations if v.manual_review_required]

    (out / "validated_telecom_task_ids.json").write_text(
        json.dumps({
            "domain": args.domain,
            "split": args.split,
            "runtime_commit": args.runtime_commit,
            "verified_dataset_commit": args.verified_commit,
            "n_total": len(validations),
            "n_validated": len(validated_ids),
            "task_ids": validated_ids,
        }, indent=2) + "\n"
    )

    # Probe summary counts
    def count(attr, val):
        return sum(1 for v in validations if getattr(getattr(v, attr), "status") == val)
    from art_p0.probes import PASS, FAIL, DETECTED, NOT_DETECTED, NOT_CONSTRUCTIBLE, NA
    summary = {
        "domain": args.domain,
        "split": args.split,
        "runtime_commit": args.runtime_commit,
        "verified_dataset_commit": args.verified_commit,
        "n_total": len(validations),
        "n_validated": len(validated_ids),
        "n_excluded": len(excluded),
        "n_manual_review": len(manual),
        "n_refusal_tasks": sum(1 for v in validations if v.task_class == "refusal"),
        "n_normal_tasks": sum(1 for v in validations if v.task_class == "normal"),
        "manifest_hash": manifest.manifest_hash(),
        "probe_summary": {
            "gold": {"PASS": count("gold", PASS), "FAIL": count("gold", FAIL)},
            "noop": {"PASS": count("noop", PASS), "FAIL": count("noop", FAIL), "NA": count("noop", NA)},
            "omission": {"DETECTED": count("omission", DETECTED), "NOT_DETECTED": count("omission", NOT_DETECTED), "NA": count("omission", NA)},
            "alternative": {"PASS": count("alternative", PASS), "NOT_CONSTRUCTIBLE": count("alternative", NOT_CONSTRUCTIBLE), "NA": count("alternative", NA)},
            "policy": {"PASS": count("policy", PASS), "FAIL": count("policy", FAIL)},
        },
        "exclusion_reason_counts": _reason_counts(excluded),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))
    return 0


def _reason_counts(excluded):
    from collections import Counter
    c = Counter(v.exclusion_reason for v in excluded)
    return dict(c)


if __name__ == "__main__":
    raise SystemExit(main())
