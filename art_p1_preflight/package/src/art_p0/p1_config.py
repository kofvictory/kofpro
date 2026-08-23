"""Frozen P1a experimental configuration (immutable once preflight starts).

Everything that defines the P1a experiment lives here so it is auditable in one
place: pinned commits, exact model snapshots, seeds, budget formulas, and the
deterministic stratified task selection.  No value here may change after the
preflight begins (task constraint §23).
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass
from typing import Any

# --- pins (must match the provenance preflight) ------------------------------
RUNTIME_COMMIT = "a2c024725189473d2d7cea3a5cfdbcc67478e41f"
VERIFIED_DATASET_COMMIT = "864350a8971a8f8ee9e7b8472e2edc380a806b0c"

# --- exact model snapshots (NO moving aliases) -------------------------------
AGENT_MODEL = "gpt-5.4-mini-2026-03-17"
AGENT_REASONING_EFFORT = "low"
USER_MODEL = "gpt-4.1-2025-04-14"

# --- fixed harness/runtime config -------------------------------------------
DOMAIN = "telecom"
SPLIT = "train"
MAX_STEPS = 100
HARNESS_IDS = ("h0", "h1", "h2")

# --- seeds (fixed in code) ---------------------------------------------------
SELECTION_SEED = 20260317          # stratified task selection
ROLLOUT_SEEDS = (1000, 2000)       # two replicate rollout seeds (scientific)
PREFLIGHT_SEED = 424242            # single preflight rollout seed

# --- sample sizes ------------------------------------------------------------
N_SCIENTIFIC = 24
N_PREFLIGHT = 3
BUDGET_LEVELS = ("low", "mid", "high")


# --- budget normalization (task constraint §12) ------------------------------
def normalized_budgets(m_x: int) -> tuple[int, int, int]:
    """Return (B_low, B_mid, B_high) for a gold assistant tool-call count.

        m'   = max(1, m_x)
        B_L  = m'
        B_M  = max(B_L + 1, ceil(1.5 m'))
        B_H  = max(B_M + 1, 2 m')

    Guarantees 1 <= B_L < B_M < B_H.
    """
    if m_x < 0:
        raise ValueError("m_x must be >= 0")
    m = max(1, int(m_x))
    b_low = m
    b_mid = max(b_low + 1, math.ceil(1.5 * m))
    b_high = max(b_mid + 1, 2 * m)
    return b_low, b_mid, b_high


def gold_assistant_tool_calls(task: Any) -> int:
    """m_x = number of ASSISTANT tool calls in the gold/reference trajectory.

    Uses ToolCallBudget semantics: individual tool calls (not messages), and
    only the agent's (assistant-requestor) calls, since the hard budget wrapper
    only charges the agent.  User-side (dual-control) gold actions are not
    charged to the agent budget and are excluded.
    """
    ec = getattr(task, "evaluation_criteria", None)
    actions = (ec.actions if ec is not None else None) or []
    return sum(1 for a in actions if getattr(a, "requestor", "assistant") == "assistant")


def task_family(task_id: str) -> str:
    """Telecom task family, e.g. 'mms_issue' from '[mms_issue]...'."""
    if task_id.startswith("[") and "]" in task_id:
        return task_id[1:].split("]", 1)[0]
    return "unknown"


# --- deterministic stratified selection --------------------------------------
@dataclass(frozen=True)
class Selection:
    scientific: list[str]
    preflight: list[str]
    strata: dict[str, list[str]]
    eligible: list[str]
    seed: int


def _largest_remainder_alloc(sizes: dict[Any, int], total: int) -> dict[Any, int]:
    """Allocate `total` items across strata proportional to `sizes`."""
    grand = sum(sizes.values())
    if grand == 0:
        return {k: 0 for k in sizes}
    raw = {k: (v * total / grand) for k, v in sizes.items()}
    floor = {k: int(math.floor(r)) for k, r in raw.items()}
    remaining = total - sum(floor.values())
    # distribute remaining by largest fractional remainder, ties broken by key
    order = sorted(sizes, key=lambda k: (-(raw[k] - floor[k]), str(k)))
    for k in order[:remaining]:
        floor[k] += 1
    # never allocate more than the stratum has
    for k in floor:
        floor[k] = min(floor[k], sizes[k])
    return floor


def stratified_select(
    tasks_meta: list[dict],
    *,
    n_scientific: int = N_SCIENTIFIC,
    n_preflight: int = N_PREFLIGHT,
    seed: int = SELECTION_SEED,
) -> Selection:
    """Deterministically select disjoint scientific + preflight task sets.

    tasks_meta: list of {"task_id", "family", "m_x"} for the ELIGIBLE pool
    (validated train tasks, manual-review excluded). Stratified by
    (family, m_x). Fully determined by `seed` and the sorted eligible list.
    """
    eligible = sorted(t["task_id"] for t in tasks_meta)
    meta = {t["task_id"]: t for t in tasks_meta}
    rng = random.Random(seed)

    # Build strata (family, m_x) with deterministic, seed-shuffled members.
    strata: dict[tuple, list[str]] = {}
    for tid in eligible:
        key = (meta[tid]["family"], meta[tid]["m_x"])
        strata.setdefault(key, []).append(tid)
    for key in strata:
        strata[key].sort()
        rng.shuffle(strata[key])

    sizes = {k: len(v) for k, v in strata.items()}

    # Scientific allocation (proportional, largest remainder).
    sci_alloc = _largest_remainder_alloc(sizes, n_scientific)
    scientific: list[str] = []
    taken: dict[tuple, int] = {}
    for key in sorted(strata, key=lambda k: str(k)):
        n = sci_alloc.get(key, 0)
        scientific.extend(strata[key][:n])
        taken[key] = n

    # Preflight: from REMAINDER, one per family where possible (disjoint).
    remainder: dict[tuple, list[str]] = {
        key: strata[key][taken.get(key, 0):] for key in strata
    }
    preflight: list[str] = []
    fams = sorted({k[0] for k in strata})
    # round-robin over families, then over remaining strata, for diversity
    fam_cycle = list(fams)
    rng.shuffle(fam_cycle)
    while len(preflight) < n_preflight:
        progressed = False
        for fam in fam_cycle:
            if len(preflight) >= n_preflight:
                break
            # pick from the largest remaining stratum of this family
            cand_keys = sorted(
                (k for k in remainder if k[0] == fam and remainder[k]),
                key=lambda k: (-len(remainder[k]), str(k)),
            )
            if cand_keys:
                k = cand_keys[0]
                preflight.append(remainder[k].pop(0))
                progressed = True
        if not progressed:
            break

    scientific = sorted(scientific)
    preflight = sorted(preflight)
    assert not (set(scientific) & set(preflight)), "scientific/preflight overlap"
    return Selection(
        scientific=scientific,
        preflight=preflight,
        strata={str(k): v for k, v in strata.items()},
        eligible=eligible,
        seed=seed,
    )


def sha256_of_obj(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def scientific_success_strict(success_official, budget_exceeded) -> Any:
    """P1 scientific outcome (task constraint §18 / P0.1 I7).

    Budget overflow is a resource-infeasible failure regardless of any partial
    benchmark progress. Otherwise strict == official.
    """
    if budget_exceeded:
        return False
    if success_official is None:
        return None
    return bool(success_official)


def _condition_hash(harness_hash: str, task_id: str, seed: int, budget: int) -> str:
    from .manifest import ExperimentCondition

    return ExperimentCondition(
        harness_hash=harness_hash, task_id=task_id, seed=seed, resource_budget=budget
    ).condition_hash()


def _row(hid, tid, level, budget, seed, harness_hash, run_prefix) -> dict:
    return {
        "run_id": f"{run_prefix}_" + sha256_of_obj([hid, tid, level, seed])[:16],
        "task_id": tid,
        "harness_id": hid,
        "harness_hash": harness_hash,
        "condition_hash": _condition_hash(harness_hash, tid, seed, budget),
        "budget_level": level,
        "tool_budget_limit": budget,
        "rollout_seed": seed,
        "agent_model": AGENT_MODEL,
        "user_model": USER_MODEL,
        "reasoning_effort": AGENT_REASONING_EFFORT,
        "runtime_commit": RUNTIME_COMMIT,
        "dataset_commit": VERIFIED_DATASET_COMMIT,
        "execution_status": "PLANNED",
    }


def build_design_rows(scientific_ids, budgets_by_task, harness_hashes) -> list[dict]:
    """The full 432-row scientific design (24 x 3 harness x 3 budget x 2 seed)."""
    rows = []
    for tid in scientific_ids:
        b = budgets_by_task[tid]
        for hid in HARNESS_IDS:
            for level in BUDGET_LEVELS:
                for seed in ROLLOUT_SEEDS:
                    rows.append(_row(hid, tid, level, b[level], seed, harness_hashes[hid], "p1a"))
    return rows


def build_preflight_rows(preflight_ids, budgets_by_task, harness_hashes) -> list[dict]:
    """The 9-row preflight design (3 tasks x 3 harness x MID budget x 1 seed)."""
    rows = []
    for tid in preflight_ids:
        b = budgets_by_task[tid]
        for hid in HARNESS_IDS:
            rows.append(_row(hid, tid, "mid", b["mid"], PREFLIGHT_SEED, harness_hashes[hid], "pf"))
    return rows


def budgets_by_task(task_ids, tasks_by_id) -> dict[str, dict[str, int]]:
    out = {}
    for tid in task_ids:
        bl, bm, bh = normalized_budgets(gold_assistant_tool_calls(tasks_by_id[tid]))
        out[tid] = {"low": bl, "mid": bm, "high": bh}
    return out
