# P0.2 — Telecom TaskValidator integration & O1/O2 fixes

**Scope:** fix the two P0.1 observations, connect the verified Telecom tasks to
the real evaluator, build the five-probe `TaskValidator`, and generate a
reproducible `D_validated`. **P0.1 was not redesigned; its budget semantics are
preserved (re-verified below).**

**Verdict: ✅ P0.2 VERIFIED** — 114/114 Telecom `base` tasks admitted, 0
excluded, 5 flagged for optional human review; ART 16/16 + 14 new unit tests
pass; P0.1 mock matrix I1–I7 still PASS.

---

## A. Repository pins

| Item | Value |
| --- | --- |
| tau2 runtime SHA (primary) | **`a2c024725189473d2d7cea3a5cfdbcc67478e41f`** (unchanged from P0.1) |
| tau2-bench-verified SHA (task source) | **`864350a8971a8f8ee9e7b8472e2edc380a806b0c`** (`git describe --always` = `864350a`) |
| Python | 3.12.3 (tau2 requires `>=3.12,<3.14`) |
| tau2 version | 1.0.1 |

**Verified-repo inspection (task §2 — "do not assume verified = correct"):**
The Telecom task data, DB, and policies are **byte-identical** between the
pinned runtime and tau2-bench-verified (`sha256` match on `tasks.json`,
`tasks_small.json`, `tasks_full.json`, `split_tasks.json`, `db.toml`,
`user_db.toml`, `main_policy.md`, `tech_support_manual.md`,
`tech_support_workflow.md`). `FIXES.md` in the verified repo documents
**only Retail and Airline** corrections — **Telecom was not among the
human-verified fixes.** The only Telecom source diff is one added
`import random` line in `tasks/manager.py` (no evaluation-semantics change).
Consequence: for Telecom, "verified" supplies the same data as the pinned
runtime, task IDs are 100% compatible, and this P0.2 validation is **genuinely
novel** task-validity work rather than a re-check of already-verified tasks.

**Telecom inventory:** 2285 semantically-distinct tasks (`full`); splits
`base`=114, `test`=40, `train`=74, `small`=20. Reward bases over the full set:
2253 `[ENV_ASSERTION]`, 32 `[ACTION, ENV_ASSERTION]`. **No task uses
`communicate_info` or `nl_assertions`**, so the entire Telecom set is graded
**without any LLM** (ENV_ASSERTION = deterministic env-state replay; ACTION =
deterministic tool-call matching). `D_validated` primary unit = the **`base`
split (114 canonical tasks)**, each fully audited by all five probes.

---

## B. O1 fix — environment-init state hash

**Implementation** (`src/art_p0/state_hash.py`): two *separate*, canonical,
deterministic fingerprints, both wired into `RunRecord`
(`task_initial_state_hash`, `environment_initial_state_hash`) and populated in
`tau3_runtime.run_tau3_once` (guarded so P0.1 fake-`api` tests still pass):

* `task_initial_state_hash(task)` — the **declared** task initial state.
* `environment_initial_state_hash(env)` — SHA-256 of a canonical snapshot of
  the **initialized** environment `{domain, agent_db, user_db}` after
  `set_state(...)`. Canonical JSON, deterministic key ordering, non-semantic
  keys (timestamps, object ids) stripped.

**Result — the P0.1 triviality is gone.** In P0.1 the mock matrix shared
`sha256("null")` for all runs. Re-running the P0.1 matrix now records the old
trivial task hash *and* a **non-trivial env hash** that captures the real mock
DB:

```
B=1  task_hash=74234e98af…(sha256 "null")   env_hash=baff4c6f79…
B=2  task_hash=74234e98af…                   env_hash=baff4c6f79…
B=4  task_hash=74234e98af…                   env_hash=baff4c6f79…
```

For Telecom the env hash is fully discriminating — e.g. two `base` tasks:
`env_hash=4f1aae25b9…` vs `e0b6e23504…`.

**Tests:** `U1` (stability: same task+runtime → identical hash), `U2`
(sensitivity: mutate one semantic device field → different hash), `U2b`
(distinct tasks differ). PASS.

---

## C. O2 fix — FrozenHarnessManifest

**Implementation** (`src/art_p0/manifest.py`). `FrozenHarnessManifest` captures
the full apparatus identity; `manifest_hash()` = SHA-256 of the canonical
harness-identity dict.

**Fields (harness identity, all in the hash):** `agent_model`,
`agent_model_args`, `agent_system_prompt_hash`, `agent_policy_prompt_hash`,
`domain_policy_text_hash`, `wrapper_class`, `budget_overflow_policy`,
`tool_schema_hash`, `tool_permissions`, `user_model`, `user_model_args`,
`max_steps`, `benchmark_runtime_commit`, `verified_dataset_commit`, `extra`.

**Experiment identity (recorded separately, NOT in the harness hash):**
`ExperimentCondition{seed, task_id, resource_budget}` with its own
`condition_hash()`.

**Rationale (`harness identity ≠ experimental-condition identity`):**
* `resource_budget` — the P0 experiment *varies* budget across runs of one
  fixed harness; folding it in would make every budget a different harness and
  break P0.1's I5 (all budgets share one harness hash).
* `seed` — re-randomization of the same apparatus (repeated measurement).
* `task_id` — selects the stimulus, not the apparatus.

**Hash behavior (tests):** `U3` budget-only change → **same** harness hash
(via `ExperimentCondition`); `U3b` seed/task change → same harness hash,
different condition hash; `U4` system-prompt change → **different** hash;
`U4b` domain-policy change → **different** hash; `U4c` model / runtime-commit /
tool-permission change → **different** hash. PASS.

---

## D. Telecom inventory (audit result)

| | count |
| --- | ---: |
| total Telecom tasks (`full`) | 2285 |
| audited (`base` split, full 5-probe) | **114** |
| validated (admitted) | **114** |
| excluded | **0** |
| manual review flagged | **5** |
| refusal / no-action tasks (special handling) | 20 |
| normal tasks | 94 |

---

## E. Probe summary (base = 114)

| Probe | Pass | Fail | Not constructible / N/A |
| --- | ---: | ---: | --- |
| Gold | 114 | 0 | 0 |
| No-op | 114 (no false positive) | 0 | 0 |
| Omission | 94 DETECTED | 0 NOT_DETECTED | 20 N/A (refusal: no mutating step) |
| Alternative | 89 | 0 | 5 NOT_CONSTRUCTIBLE (normal) · 20 N/A (refusal) |
| Policy | 114 | 0 | 0 |

**Broadening beyond `base`** (to avoid over-fitting the conclusion to 114
tasks — logs/broad_scan_findings.txt):
* Structural scan over **all 2285**: 32 refusal tasks, **0** not gated by
  ACTION/COMMUNICATE (i.e. no refusal task is a no-op false positive).
* No-op false-positive hunt over a **600-task** random sample of the 2253
  ENV_ASSERTION-only tasks: **0** found.
* Gold/no-op/omission over a **150-task** random sample *outside* `base`:
  gold 150/150 PASS, no-op 150/150 clean, omission 150/150 DETECTED-or-N/A.

**Strict success layer:** `success_strict = success_official ∧` sourced
semantic checks (all env_assertions met — source `evaluation_criteria.env_assertions`;
all reference actions matched when ACTION ∈ basis — source `reward_basis`;
required mutations present — source reference actions). For all 114 admitted
tasks `success_strict = success_official = True` on the gold reference.

---

## F. Top grader/task problems found

No task in `base` (or the broader samples) failed gold, produced a no-op false
positive, hid an undetected omission, or showed a policy/tool/evaluator
mismatch. The findings below are **design observations**, ordered by severity;
none forced an exclusion.

1. **[medium] Refusal tasks lean entirely on the ACTION check.** For the 20
   `service_issue` refusal tasks (`transfer_to_human_agents` only), the
   `ENV_ASSERTION` (`assert_service_status = no_service`) is satisfied by
   **inaction** — the correct end-state equals the broken initial state.
   Concretely, gold and no-op both give `ENV_ASSERTION=1.0`; only
   `ACTION(transfer)=1.0 vs 0.0` separates them. These tasks are **valid only
   because ACTION ∈ reward_basis** gates the escalation. A hypothetical refusal
   task with `reward_basis=[ENV_ASSERTION]` alone would be a silent no-op false
   positive — we scanned all 2285 and found **0** such tasks, but the pipeline
   now flags `refusal_not_gated_by_action_or_communicate` if one ever appears.
2. **[low] 5 normal tasks are order-dependent (alternative NOT_CONSTRUCTIBLE).**
   For 5 multi-issue `mms_issue`/`service_issue` tasks the two tested
   reorderings (reversed, rotate-1) did not reach the asserted end-state, so no
   safe alternative route was *provable* — reported `NOT_CONSTRUCTIBLE` and
   flagged for human review rather than fabricating a route. This is expected
   for genuinely sequenced repairs (e.g. fix APN before enabling data); it is
   **not** evidence of grader over-constraint (the grader is end-state based).
3. **[informational] Telecom is not in the "verified" corrections.**
   tau2-bench-verified fixed only Retail/Airline; Telecom validity here rests on
   this P0.2 audit, not on amazon-agi's human verification (§A).

---

## G. Validated slice

`runs/validated_telecom_task_ids.json` (D_validated):

```json
{ "domain": "telecom", "split": "base",
  "runtime_commit": "a2c024725189473d2d7cea3a5cfdbcc67478e41f",
  "verified_dataset_commit": "864350a8971a8f8ee9e7b8472e2edc380a806b0c",
  "n_validated": 114, "task_ids": [ … 114 ids … ] }
```

Machine-readable artifacts (all under `runs/`):
`telecom_task_audit.jsonl` / `.csv` (per-task rows incl. both hashes,
probe outcomes, strict layer, flags), `validated_telecom_task_ids.json`,
`excluded_telecom_tasks.jsonl` (empty — 0 exclusions),
`frozen_harness_manifest.json` (example manifest + hash),
`artifacts/<task>/{gold,noop,omission,alternative}.json` (114 dirs),
`summary.json`.

---

## H. Test results

```
ART P0.1 baseline (fakes + real tau2): 16/16 PASS
New P0.2 unit tests:                   14/14 PASS   (U1–U7 + variants)
  test_p02_state_hash.py   3   (U1, U2, U2b)
  test_p02_manifest.py     6   (U3, U3b, U4, U4b, U4c, determinism)
  test_p02_probes.py       3   (U5, U5b, U6)
  test_p02_determinism.py  2   (U7, U7b)
Total: 30/30 PASS
Integration (regression): P0.1 contract PASS; P0.1 real mock matrix I1–I7 PASS
  (budget semantics preserved); Telecom base pipeline 114/114 admitted.
```

---

## I. Patch summary

Additive changes to the ART package — **no P0.1 logic altered, no refactor**
(constraint 10). Budget/adapter/trajectory/hashing/validator modules untouched.

**Modified (3):**
* `src/art_p0/__init__.py` — export the new O1/O2 symbols.
* `src/art_p0/ledger.py` — **+2 optional fields** (`task_initial_state_hash`,
  `environment_initial_state_hash`, default `None`; all pre-existing ledgers
  stay valid).
* `src/art_p0/tau3_runtime.py` — populate the two hashes in `run_tau3_once`,
  fully guarded (fake-`api` unit tests unaffected).

**Added (8):**
* `src/art_p0/state_hash.py` (O1, 169 lines)
* `src/art_p0/manifest.py` (O2, 221 lines)
* `src/art_p0/probes.py` (5-probe pipeline, 562 lines)
* `scripts/validate_telecom.py` (D_validated CLI, 217 lines)
* `tests/test_p02_state_hash.py`, `tests/test_p02_manifest.py`,
  `tests/test_p02_probes.py`, `tests/test_p02_determinism.py`

The five-probe pipeline grades synthesized trajectories with the **real**
`tau2.evaluator.evaluate_simulation`; it uses **no Orchestrator and no LLM**, so
the verified P0.1 budget path is not on the P0.2 code path at all.

---

## J. Verdict

### ✅ P0.2 VERIFIED

* O1 fixed (env-init hash, non-trivial & sensitive; U1/U2 pass).
* O2 fixed (FrozenHarnessManifest; budget-invariant, prompt/policy-sensitive;
  U3/U4 pass).
* Telecom verified tasks connected to the real evaluator (LLM-free).
* Five-probe `TaskValidator` built; `D_validated(base)` = **114/114** admitted,
  0 excluded, 5 flagged for optional human review.
* P0.1 budget semantics preserved (I1–I7 re-verified); 30/30 tests pass.

Scientific guardrails honored: validity is **not** defined by benchmark reward
alone (admission needs no-op-negative + omission-detectable + policy-consistent);
the reference sequence is not assumed unique (alternative probe) nor individually
necessary (omission measures load-bearing empirically); no-op false positives and
refusal-gating were actively hunted (0 found across 2285); every decision and
reason code is persisted; dataset/runtime commits are pinned.

## K. Next-step recommendation

> **Proceed to P1 fixed-harness calibration experiment.**

Instantiate a concrete `FrozenHarnessManifest` (fill `agent_model`/`user_model`
and freeze the prompts) over `D_validated` (base, 114). When the standard
held-out set is preferred, re-run `validate_telecom.py --split test` (and
`train`) to extend `D_validated` under the identical pipeline — the slice is
deterministic in `(runtime_commit, verified_dataset_commit, split)` (U7).

---

### Reproduction

```bash
git -C tau2-bench rev-parse HEAD            # a2c024725189473d2d7cea3a5cfdbcc67478e41f
git -C tau2-bench-verified rev-parse HEAD   # 864350a8971a8f8ee9e7b8472e2edc380a806b0c
uv pip install -e tau2-bench 'package[dev]'          # Python 3.12
python -m pytest -q package                          # 30 passed
python package/scripts/validate_telecom.py --split base --out runs   # 114/114 admitted
```
