# ART P0 Instrumentation v0.2 — End-to-End Verification against τ² / τ³

**Audit type:** implementation audit (verification only — no new features).
**Goal:** confirm the ART P0 instrumentation preserves measurement semantics
when run on the *real* current tau2/τ³ runtime, not merely on the local fakes.
**Date:** 2026-08-20
**Result:** ✅ **P0.1 VERIFIED** (no adapter patches were required).

All commands were run inside a pinned tau2 checkout with two Python
environments (see below). Raw stdout/stderr is preserved under
`logs/`; machine-readable results under `runs/`.

---

## A. Repository

| Item | Value |
| --- | --- |
| Primary repository | `https://github.com/sierra-research/tau2-bench` |
| **Pinned commit SHA** | **`a2c024725189473d2d7cea3a5cfdbcc67478e41f`** |
| `git describe --tags` | `v1.0.1-31-ga2c0247` (31 commits after tag `v1.0.1`) |
| Package version | `tau2 1.0.1` (from `pyproject.toml`; installed metadata `1.0.1`) |
| Latest commit subject | `Update Pine Voice leaderboard metadata (#482)` |
| **Python requirement** | tau2: `>=3.12,<3.14` · ART: `>=3.10` |
| Install command | `uv pip install -e .` (tau2) + `uv pip install -e '.[dev]'` (art-p0) |
| **Installation status** | ✅ Installed & imported successfully on **CPython 3.12.3** |

**Breaking / relevant API notes for our adapter:** none found. The public
"power-user" API the adapter targets is present and matches (see §B). One
environment note: **ART declares `requires-python >=3.10`, but tau2 requires
`>=3.12`.** A combined environment therefore *must* use Python 3.12/3.13
(3.11 will not resolve tau2). This is an environment constraint, not a code
defect. `tau2` registers domains lazily on import; `mock` is registered by
default (no extras needed for P0).

---

## B. Contract result — **PASS** (no patch)

Ran the zero-LLM contract check against the installed checkout:

```bash
python scripts/check_tau3_contract.py    # -> {"ok": true}, exit 0
```

Every public symbol the adapter depends on was verified against the **actual
upstream source** at the pinned SHA (not guessed):

| Contract surface | Upstream location @ `a2c0247` | Verdict |
| --- | --- | --- |
| `HalfDuplexAgent` (`get_init_state`, `generate_next_message`, `stop`, `set_seed`) | `tau2/agent/base_agent.py` + `agent/base/participant.py` | ✅ signatures match the wrapper exactly |
| `LLMAgent(tools, domain_policy, llm, llm_args)` | `tau2/agent/llm_agent.py:61` | ✅ ctor matches `tau3_runtime` call |
| `Orchestrator(domain, agent, user, environment, task, max_steps, max_errors, seed, validate_communication, …)` | `tau2/orchestrator/orchestrator.py:394` | ✅ all kwargs accepted |
| `orchestrator.agent_state / step_count / termination_reason / get_messages() / trajectory` | `orchestrator.py` (127, 134, 136, 177, 448) | ✅ all present & consumed correctly |
| `get_tasks(task_set, …, task_ids=)` | `tau2/runner/helpers.py:56` | ✅ |
| `build_environment(domain)` | `tau2/runner/build.py:41` | ✅ |
| `build_user(user_name, env, task, llm=, llm_args=)` | `tau2/runner/build.py:128` | ✅ |
| `run_simulation(orchestrator, *, evaluation_type=)` → `SimulationRun` | `tau2/runner/simulation.py:19` | ✅ |
| `EvaluationType.ALL` | `tau2/evaluator/evaluator.py:24` | ✅ |
| mock domain + `create_task_1` | `data/tau2/domains/mock/tasks.json`; used verbatim in `tau2/run.py:20` | ✅ exactly 1 task, id matches |
| `AssistantMessage.tool_calls: Optional[list[ToolCall]]` | `tau2/data_model/message.py:205` | ✅ budget counter semantics correct (None → 0) |
| `SimulationRun.reward_info.reward / termination_reason / agent_cost / messages` | `tau2/data_model/simulation.py:1267` + `RewardInfo.reward:1078` | ✅ all fields the runtime reads exist |

**Key semantic confirmation:** base `LLMAgent` does **not** override the
`is_stop` classmethod (only `LLMSoloAgent` does). The wrapper subclasses
`HalfDuplexAgent` and likewise leaves `is_stop → False`, so it faithfully
mirrors the standard `LLMAgent`; termination is driven by the user/max-steps,
exactly as upstream expects. Runtime confirmation: `BudgetEnforcingAgent`
resolves to a genuine subclass of the real `HalfDuplexAgent`
(`HalfDuplexAgent in BudgetEnforcingAgent.__mro__ == True`, object-fallback
inactive).

---

## C. Tests

```text
ART tests (local fakes, Python 3.11):        16/16 PASS
ART tests (real tau2 installed, Python 3.12): 16/16 PASS
tau integration matrix (real Orchestrator):   PASS (all invariants I1–I7)
```

With tau2 installed, `test_tau_adapter_import` / `test_tau_adapter_behavior`
exercise the **real** `HalfDuplexAgent` subclass path (not the `object`
fallback). Logs: `logs/art_tests_baseline.log`, `logs/phase3_arttests_tau2.log`.

---

## D. Mock matrix — real τ³ Orchestrator, deterministic (no-LLM) policies

The matrix was executed on the **real** tau2 `Orchestrator` + `mock`
`Environment` + real evaluator (`EvaluationType.ALL`, which for `create_task_1`
reduces to `DB` + `COMMUNICATE` — no LLM judge, since the task's default
`reward_basis=[DB, COMMUNICATE]` contains no `NL_ASSERTION`). Only the *policy
source* was swapped for a fixed, **budget-independent** scripted agent/user,
injected through the adapter's documented `api=` seam
(`art_p0.tau3_runtime.run_tau3_once(..., api=...)`). **No ART package code was
modified.** Driver: `phase4_real_matrix.py`. Task `create_task_1`, seed `42`.

Scripted agent's fixed action sequence (identical at every budget):
`create_task(user_1,"Important Meeting")` → `get_users()` → `get_users()` →
closing text. The ART `ToolCallBudget` ceiling is the *only* thing that
differs between rows.

| Budget | Tool calls used | Reward | Budget exceeded | Termination | Initial-state hash |
| -----: | --------------: | -----: | --------------- | ----------- | ------------------ |
| 1 | 1 | — (not scored) | **true** | `ART_BUDGET_EXCEEDED` | `74234e98afe7…` |
| 2 | 2 | — (not scored) | **true** | `ART_BUDGET_EXCEEDED` | `74234e98afe7…` |
| 4 | 3 | **1.0** | false | `user_stop` | `74234e98afe7…` |

Invariant results (`runs/phase4_summary.json`, `logs/phase4_matrix.log`):

- **I1 — budget ceiling** `n_used ≤ B`: PASS (1≤1, 2≤2, 3≤4).
- **I2 — atomic overflow**: PASS. A single message carrying a **batch of 2**
  tool calls at `B=1` raised `BudgetExceeded(requested=2, remaining=1)`
  **before any call executed**; verified against the live mock DB that **no
  task was created** (`db_unchanged=true`, `budget_used_after=0`). No partial
  batch execution.
- **I3 — initial-state equality**: PASS (identical hash across budgets).
- **I4 — fresh environment**: PASS (3 distinct `id(env)` — a new `Environment`
  is constructed per experimental unit).
- **I5 — harness equality**: PASS (single harness hash `62dc171e5ed1…` across
  all budgets; budget is deliberately excluded from the harness identity).
- **I6 — persistence**: PASS (3 ledger JSONL rows + 3 trajectory JSON files;
  offline auditor `check_p0_invariants.py` → `records=3, failures=0`).
- **I7 — infeasible-policy semantics**: PASS. Both budget-exceeded runs are
  `budget_exceeded=true, success_official=false` **even though the gold
  `create_task` action had already mutated the DB** at `B=1`. Intermediate
  benchmark progress does **not** rescue a resource-exhausted run — exactly the
  intended measurement-layer semantics.
- Nested-budget monotonicity (README invariant 3): PASS (used = 1,2,3 is
  non-decreasing in B for the same policy).

---

## E. Bugs found

**No correctness bugs.** The instrumentation runs on the real tau2 runtime
without altering benchmark semantics, agent policy, or reset behavior.

Two **non-blocking observations** (recommendations for the Telecom stage, not
defects — deliberately *not* patched, per the "no scope creep / minimal
adapter changes" constraint):

| # | Severity | Location | Observation |
| - | -------- | -------- | ----------- |
| O1 | Low / informational | `tau3_runtime.py::_task_initial_state_fingerprint` | The I3 fingerprint hashes `task.initial_state`, which is `None` for every `mock` task (`create_task_1` has no `initial_state`). The reported hash `74234e98afe7…` is exactly `sha256("null")`, so I3 holds only *trivially* here; the true initial DB state (`user_1 → [task_1]`, from the domain default DB) is **not** captured by this fingerprint. Reset correctness is still independently covered by I4 (distinct fresh `Environment` objects) + deterministic default DB. **Recommendation:** before Telecom, also hash a snapshot of the environment DB *after* `Orchestrator.initialize()`, since Telecom tasks *do* carry meaningful `initial_state`. |
| O2 | Low / informational | `tau3_runtime.py` `harness_cfg` | The frozen harness hash covers `agent_llm`, `agent_llm_args`, wrapper class, and overflow policy, but **not** the domain-policy text, `user_llm`, `seed`, `task_id`, or `max_steps`. I5 (budget-invariance) and README invariant 4 (agent/wrapper/overflow change ⇒ new hash) both hold, and `check_matrix_invariants` independently guards `seed`/`task_id`/initial-state. **Recommendation:** fold policy text + user-model identity into the preregistered harness manifest before scientific rollout so "frozen harness identity" is complete. |

---

## F. Patch

**No files in the ART package were changed.** `git` shows the audited artifact
(`audited_artifact/`) is byte-identical to the delivered ZIP.

Added (audit scaffolding only, outside the ART package):

- `phase4_real_matrix.py` — real-Orchestrator, no-LLM budget-matrix driver +
  explicit I1–I7 assertions and the atomic-overflow DB probe. Uses only the
  public `api=` seam; injects real `get_tasks`/`build_environment`/
  `Orchestrator`/`run_simulation`/`EvaluationType` and scripted (non-LLM)
  agent/user *policies*.
- `logs/`, `runs/` — preserved command output, ledger, trajectories, summary.

---

## G. Verdict

### ✅ P0.1 VERIFIED

- Contract: **PASS** against pinned tau2 `a2c0247` (no patch).
- ART tests: **16/16** on fakes *and* **16/16** with real tau2 installed.
- Real-Orchestrator mock matrix (B ∈ {1,2,4}, seed 42): **all invariants
  I1–I7 PASS**, including atomic multi-call overflow verified against the live
  mock DB and infeasible-policy failure semantics.
- Phase 5 (real-model smoke): **SKIPPED** — no API credentials were present in
  the environment (none requested or displayed, per instructions).

## H. Next-step recommendation

> **Proceed to Verified Telecom TaskValidator integration.**

Carry the two low-severity observations (O1: hash post-`initialize()` env DB;
O2: complete the frozen-harness manifest) into that stage, because Telecom
tasks carry real `initial_state` and richer policies where both currently make
a material difference. Record the pinned benchmark SHA
`a2c024725189473d2d7cea3a5cfdbcc67478e41f` in the experiment manifest and do
not mix runs across τ³ revisions.

---

### Reproduction

```bash
# 1. Pin tau2 (Python 3.12/3.13 required by tau2)
git clone https://github.com/sierra-research/tau2-bench
git -C tau2-bench rev-parse HEAD          # a2c024725189473d2d7cea3a5cfdbcc67478e41f
uv venv --python 3.12 .venv && source .venv/bin/activate
uv pip install -e tau2-bench

# 2. Install ART P0 (unmodified) in the same env
uv pip install -e 'audited_artifact[dev]'

# 3. Phase 2 — contract (no LLM)
python audited_artifact/scripts/check_tau3_contract.py     # {"ok": true}

# 4. Phase 3 — ART tests
python -m pytest -q audited_artifact                        # 16 passed

# 5. Phase 4 — real Orchestrator matrix (no LLM)
python phase4_real_matrix.py runs                           # PHASE4=PASS
python audited_artifact/scripts/check_p0_invariants.py runs/p0_real_matrix.jsonl
```
