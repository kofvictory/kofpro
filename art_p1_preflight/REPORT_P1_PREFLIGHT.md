# P1a Preflight — implementation, freeze, and readiness (NOT executed)

**Scope:** verify P0 provenance, validate the Telecom **train** split, freeze the
P1 configuration (models, 3 harnesses, budgets, task sample, 432-run design),
run all tests, and — only if credentials exist — run **exactly 9** paid preflight
rollouts. **The 432 scientific rollouts were NOT executed and must not be.**

**Verdict: ✅ P1 PREFLIGHT READY — NOT EXECUTED** (API credentials absent; all
implementation and offline verification complete; one MAJOR design observation
for human review — see §J).

---

## A. Provenance

| Item | Value |
| --- | --- |
| tau2 runtime SHA | `a2c024725189473d2d7cea3a5cfdbcc67478e41f` ✅ matches pin |
| tau2 working tree | **clean** (`git status --porcelain` empty; `git diff HEAD` & `--cached` exit 0) → `TAU_RUNTIME_PROVENANCE_OK` |
| verified dataset SHA | `864350a8971a8f8ee9e7b8472e2edc380a806b0c` ✅ matches pin → `VERIFIED_DATASET_PROVENANCE_OK` |
| Python | 3.12.3 |
| ART package (kofpro branch) | `claude/art-p0-tau-verification-dmkm2c` (this commit) |

Neither repository was upgraded. No benchmark-runtime files were modified.

## B. Train validation (D_validated_train)

Ran the **unchanged** P0.2 five-probe validator on the Telecom **train** split
(`runs/p1_train_validation/`):

| | count |
| --- | ---: |
| total train tasks | 74 |
| validated (admitted) | **74** |
| excluded | 0 |
| manual-review flagged (excluded from P1a) | 3 |
| **P1a-eligible pool** (validated ∧ ¬manual-review) | **71** |

Probe summary (train): gold 74/74 PASS · no-op 74/74 (no false positive) ·
omission 66 DETECTED + 8 N/A (refusal) · alternative 63 PASS + 3
NOT_CONSTRUCTIBLE + 8 N/A · policy 74/74. `D_validated_train` = 74 admitted;
the 3 manual-review tasks are held out of P1a. **71 ≥ 30**, so the run proceeds.
The held-out **test** split was never loaded for selection or rollout (P1-U5).

## C. Model configuration

| Role | Exact snapshot | Args |
| --- | --- | --- |
| Agent | `gpt-5.4-mini-2026-03-17` | `reasoning_effort=low` |
| User simulator | `gpt-4.1-2025-04-14` | — |

**Adapter/endpoint:** tau2 `generate()` (`tau2/utils/llm_utils.py`) forwards
`model` and `**llm_args` (including `reasoning_effort`) directly to
`litellm.completion(...)` with **no model-name whitelist**. The exact snapshots
therefore pass unmodified; `reasoning_effort` rides in the agent's `llm_args`.
**No benchmark-runtime patch was required** (no ART-side model-compat patch
needed either). No moving aliases are used.

## D. Frozen harnesses

All three share model, reasoning effort, tools, tool permissions, domain policy,
`max_steps=100`, user simulator, execution environment, and benchmark commits.
Only the harness policy differs.

| Harness | Hash (first 16) | Intended contrast |
| --- | --- | --- |
| h0 | `67e36ec8a5136f10` | nominal |
| h1 | `59e525755f4cb370` | budget awareness (`h1−h0`) |
| h2 | `621fc3fd4a0047ac` | plan-and-verify (`h2−h1`) |

**Prompt deltas (exact):**

* **h0 nominal** — standard tau `LLMAgent` under the P0.1-verified
  `BudgetEnforcingAgent`. The hard budget is enforced; remaining budget is **not**
  exposed to the model.
* **h1 budget-aware** — h0 plus, appended to the system message **each turn**:
  ```
  Hard tool-call budget remaining: {remaining}.
  Use the available calls carefully. You may stop before exhausting the budget.
  ```
  (`{remaining}` filled per turn by the enforcing wrapper; no planning/verification/domain advice.) Wrapper = `BudgetAwareEnforcingAgent` (subclass of the verified wrapper; enforcement unchanged).
* **h2 budget-aware + plan-verify** — h1 plus, added to the system `<instructions>`:
  ```
  Before taking consequential actions, identify the task goal, the information
  required to complete it, and the likely state-changing actions.
  Before an irreversible or state-changing tool action, verify that its
  prerequisites are satisfied.
  Do not reveal private chain-of-thought. Only produce the tool calls and
  user-facing responses needed to perform the task.
  ```
  (task-agnostic; no Telecom workflow encoded.)

Manifests: `runs/manifests/h{0,1,2}.json` (each carries its `manifest_hash`).
Enforcement of the atomic hard budget (P0.1 I2/I7) is inherited unchanged — the
P0.1 real-mock matrix still passes I1–I7 (regression re-run, §G).

## E. Task selection

| | value |
| --- | --- |
| eligible pool | 71 (validated train, manual-review removed) |
| scientific selection seed | `20260317` (**unchanged**) |
| scientific tasks | **24** → `runs/p1_task_sample.json` (**frozen, unchanged**) |
| preflight selection seed | `20260318` (v2) |
| preflight-only tasks | **3** → `runs/p1_preflight_tasks.json` (**re-selected, v2**) |
| overlap | **∅** (structural: preflight drawn from eligible − scientific) |

**Scientific sample (unchanged).** Deterministic, stratified by (task family ×
gold assistant tool-call count `m_x`), proportional largest-remainder,
seed-shuffled within strata; no hand-picking. Stratification: family
{mms_issue:10, mobile_data_issue:9, service_issue:5}; `m_x` {0:4, 1:13, 2:7}.
Re-verified byte-identical after the preflight re-selection (identical
`task_ids` **and** identical `artifact_sha256`) — P1-U15.

**Preflight sample v2 (re-selected).** v1 picked one task per *family* but all
three happened to have `m_x = 1`, so at MID budget every preflight run sat at a
single point of the resource interface and the ceiling could barely engage.
v2 selects **one task per distinct `m_x` level {0, 1, 2}**, drawn from the pool
*excluding* the scientific 24 (n=47), with families **maximally spread**
(all three distinct). Deterministic given (pool, `PREFLIGHT_SELECTION_SEED`).
Zero paid rollouts had been executed, so re-selecting preflight-only tasks costs
nothing scientifically and is not adaptive modification of the experiment.

| m_x | B_mid | family | task |
| ---: | ---: | --- | --- |
| 0 | 2 | mms_issue | `[mms_issue]airplane_mode_on\|bad_network_preference\|bad_wifi_ca…` |
| 1 | 2 | mobile_data_issue | `[mobile_data_issue]data_saver_mode_on\|data_usage_exceeded…` |
| 2 | 3 | service_issue | `[service_issue]airplane_mode_on\|break_apn_settings\|overdue_bil…` |

Each artifact embeds its seed, eligible population, selection rule + rationale,
per-task `m_x`/family/`B_mid`, both commits, and its own SHA-256.

## F. Budget table (`runs/p1_budget_table.csv`)

`m'=max(1,m_x)`, `B_L=m'`, `B_M=max(B_L+1,⌈1.5m'⌉)`, `B_H=max(B_M+1,2m')`
(implemented exactly; all rows satisfy `1≤B_L<B_M<B_H`).

| gold assistant tool-calls `m_x` | tasks | B_low | B_mid | B_high |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 4 | 1 | 2 | 3 |
| 1 | 13 | 1 | 2 | 3 |
| 2 | 7 | 2 | 3 | 4 |

`m_x` counts **assistant** tool calls in the gold trajectory (ToolCallBudget
semantics: individual calls, agent-side only). Per §13, `B_low = m_x` guarantees
a known valid trajectory fits the nominal ceiling; **no minimality is claimed**.

## G. Tests

```
P0.1 + P0.2 regression:            30/30 PASS
P1 tests (P1-U1 … P1-U15):         22/22 PASS   (U6 is 6 parametrized cases)
TOTAL:                             52/52 PASS
P0.1 budget regression (I1–I7):    PASS  (atomic overflow + infeasible-failure preserved)
Offline harness wiring smoke:      h0/h1/h2 agents + Orchestrator construct with NO model call
```

P1 test map: U1 budget-invariant harness hash · U2 harness-distinct hashes ·
U3 deterministic sample · U4 disjoint sets · U5 no test-split leakage ·
U6 budget formula · U7 =432 rows · U8 =9 rows · U9 two replicate seeds/condition ·
U10 selected⊆eligible · U11 commits match pins · U12 overflow⇒strict-fail ·
**U13 preflight spans m_x {0,1,2} + 3 distinct families · U13b preflight
selection deterministic · U14 `ceiling_engaged` semantics · U14b GREEN/YELLOW/RED
thresholds · U15 scientific 24 unchanged (hash self-consistent)**.

## H. Preflight results

**NOT EXECUTED — API credentials are not present in the environment.**
`scripts/run_preflight.py` re-checked the environment, found no credentials, and
exited **without any API call**, emitting
`P1 PREFLIGHT READY — API CREDENTIALS NOT PRESENT`. Confirmed afterwards:
**no ledger file (`p1_preflight.jsonl` absent) and 0 trajectory files** — i.e.
zero paid rollouts. No mock or simulated results were substituted (§16).

The 9 preflight rows are staged and immutable in `runs/preflight_design.jsonl`
(all `run_id` prefixed `pf_`, `budget_level=mid`, `rollout_seed=424242`;
B_mid = 2, 2, 3 across the three tasks). The executor implements the complete
per-run reporting schema requested — budget limit, used tool calls, budget
exceeded, **ceiling_engaged**, strict success, official success, token usage
(prompt/completion/reasoning/cached where the provider exposes them), agent
cost, user-simulator cost, total cost, wall time, turns, termination reason —
and writes `runs/preflight_runs_table.json` plus `runs/preflight_cost_summary.json`.

### H.1 Ceiling engagement — **UNDETERMINED (0 runs)**

`ceiling_engaged = (used_calls == B) ∨ budget_exceeded` is implemented and
unit-tested (U14), and the classifier (U14b) is:

| verdict | criterion |
| --- | --- |
| GREEN | ≥3/9 runs engaged **and** engagement on ≥2 distinct preflight tasks |
| YELLOW | 1–2/9 engaged (also: ≥3 but concentrated on a single task) |
| RED | 0/9 engaged |

**No verdict can be issued**: GREEN/YELLOW/RED is defined over 9 executed runs
and 0 were executed. Reporting RED here would be wrong — RED means "the ceiling
was observed never to engage", which is an empirical claim requiring data.
The current state is **UNDETERMINED — awaiting credentials**.

## I. Cost projection

**Deferred — requires the 9 preflight runs; 0 executed.** Per §16/§19 the primary
estimate must come from **observed provider usage/cost metadata**, which does not
exist with zero runs; no public-price surrogate is presented as an estimate.
The procedure is implemented and will, once the 9 runs exist, emit
`runs/preflight_cost_summary.json` with:

* `ĉ_run = (Σ observed API cost)/9`, plus median, min/max, agent-only mean,
  user-sim-only mean, mean tokens by harness, mean wall time;
* `Ĉ₄₃₂ = 432·ĉ_run`; `Ĉ_safe = 1.20·432·ĉ_run`.

If provider dollar cost is unavailable, cost is reconstructed from actual token
usage × pinned model pricing and **labeled "RECONSTRUCTED"**.

## J. Problems discovered

| Severity | Finding |
| --- | --- |
| **MAJOR** | **Telecom agent tool-call budget is intrinsically small.** Because Telecom is dual-control, most gold actions are **user-side** device toggles; the **agent's** gold tool-call count is `m_x ∈ {0,1,2}` across the entire train pool (0→14, 1→38, 2→22 of 74). Normalized budgets are therefore `B∈{1,2,3,4}`, and the budget ceiling may rarely bind for the agent. The `h1−h0` / budget-response contrast may be weak on Telecom. This is surfaced for **human design review** before authorizing the 432 runs; it is **not** patched (no adaptive redesign — §23). It does not affect measurement validity (budget semantics are exact), only the expected effect size. **The v2 preflight re-selection (§E) and the new `ceiling_engaged` diagnostic exist precisely to let the 9-run preflight measure whether this risk is real before any scientific spend.** |
| **MINOR (resolved)** | **v1 preflight tasks were `m_x`-degenerate.** All three v1 preflight tasks had `m_x=1`, so the 9 runs would all have probed one point of the resource interface and could not have distinguished "ceiling never engages" from "we never sampled where it would". Fixed by the v2 re-selection spanning `m_x ∈ {0,1,2}` with 3 distinct families. Legitimate because **zero paid rollouts had been executed** — no result influenced the change (not adaptive modification under §23), and the scientific 24 are provably unchanged (U15). |
| INFORMATIONAL | **Instruction ambiguity, recorded.** The re-selection request arrived with one corrupted character (`preflight専用3 taskだけを 「�」 をそれぞれ代表するように再選択`). Interpreted as **`m_x` levels**, because (a) the preflight design is fixed at MID budget so "budget levels" cannot vary within it, (b) `m_x ∈ {0,1,2}` has exactly 3 levels for exactly 3 preflight slots, and (c) it directly serves the stated `ceiling_engaged` objective. Recorded here rather than silently chosen, per the standing instruction to document interpretation risks. Preflight tasks can never enter the scientific sample, so this choice cannot bias P1a. |
| INFORMATIONAL | 20/74 Telecom gold trajectories have `m_x=0` assistant calls (agent only communicates / escalates). `m'=max(1,m_x)` still yields a valid `B_low=1`, so `B_low` may exceed the reference agent tool-call count for these — expected under the §12 floor, not a defect. |
| INFORMATIONAL | Telecom was **not** in the tau2-bench-verified human corrections (Retail/Airline only); train-split validity rests on the P0.2 audit (all probes clean here). |
| INFORMATIONAL | `reasoning_effort=low` and the 2026 agent snapshot are not in litellm's cost map; §I cost will be reconstructed from token usage × pinned pricing and labeled as such. |

## K. Verdict

### ✅ P1 PREFLIGHT READY — NOT EXECUTED

Provenance verified; train split validated (71 eligible ≥ 30); models frozen and
adapter-compatible with no runtime patch; three harnesses frozen with distinct
hashes and exact prompt deltas; the **24 scientific tasks, h0/h1/h2, budget
formula and model snapshots are unchanged**; the 3 preflight-only tasks were
re-selected (v2) to span `m_x ∈ {0,1,2}` with 3 distinct families and remain
disjoint from the scientific set; budgets and the 432-row + 9-row designs
regenerated and asserted; **52/52 tests pass**; P0.1 budget semantics preserved
(I1–I7). The 9 paid preflight rollouts are blocked solely by absent API
credentials — 0 executed, no ledger, no trajectories. Ceiling-engagement verdict
is therefore **UNDETERMINED**, and cost projection is deferred. The 432
scientific rollouts were **not** executed.

## L. Recommendation

**Ready for human review before authorizing the 432-run P1a experiment.**
Next action is operational, not scientific: **provision API credentials** and
re-run `scripts/run_preflight.py` — it will execute exactly the 9 staged rows,
emit the full per-run table, the GREEN/YELLOW/RED ceiling verdict, and the
`Ĉ₄₃₂` / `1.2·Ĉ₄₃₂` projection with no further code changes.

Reviewers should then weigh the MAJOR finding in §J (small agent tool-call budget
on Telecom) together with the ceiling verdict:
* **GREEN** → the resource interface bites; P1a as designed is informative.
* **YELLOW / RED** → the budget manipulation may be too weak on Telecom; consider
  a domain or resource-interface change **before** spending 432 runs. Note that
  any such change requires a **new experiment version identifier**, not an edit
  to this frozen design.

Do not start P1a.

---

### Scientific interpretation constraint (§27)

P1a does **not** measure unrestricted or intrinsic model capability. At most it
estimates performance under: fixed model × fixed task distribution × fixed
execution-resource interface × fixed declared harness class. The (future) 9-run
preflight is engineering verification and cost estimation only — never evidence
about harness superiority.

### Patch summary (vs P0.2 package)

Additive only; no P0.1/P0.2 core logic changed (budget, tau_adapter, probes,
state_hash, ledger, tau3_runtime untouched).
* **Modified (2):** `src/art_p0/__init__.py` (P1 note), `src/art_p0/manifest.py`
  (+`reasoning_effort` field; `wrapper_class` threaded through the builder).
* **Added (6):** `src/art_p0/harnesses.py`, `src/art_p0/p1_config.py`,
  `src/art_p0/p1_rollout.py`, `scripts/build_p1a.py`, `scripts/run_preflight.py`,
  `tests/test_p1_preflight.py`.

**v2 delta (preflight re-selection + ceiling instrumentation), 4 files:**
* `src/art_p0/p1_config.py` — added `PREFLIGHT_SELECTION_SEED`,
  `select_preflight_by_mx()`, `ceiling_engaged()`,
  `summarize_ceiling_engagement()`. `SELECTION_SEED`, `stratified_select()`,
  `normalized_budgets()`, and all model constants are **untouched**.
* `src/art_p0/p1_rollout.py` — records `metadata.ceiling_engaged` per run.
* `scripts/build_p1a.py` — preflight now drawn from (eligible − scientific) via
  `select_preflight_by_mx`; scientific path unchanged; richer preflight artifact.
* `scripts/run_preflight.py` — full per-run reporting table, ceiling
  GREEN/YELLOW/RED classification, cost projection incl. 20 % margin.
* `tests/test_p1_preflight.py` — +5 tests (U13, U13b, U14, U14b, U15).

### Artifacts

`runs/manifests/h{0,1,2}.json` · `runs/p1_train_validation/` ·
`runs/p1_task_sample.json` · `runs/p1_preflight_tasks.json` ·
`runs/p1_budget_table.csv` · `runs/p1a_design.jsonl` (432, PLANNED) ·
`runs/preflight_design.jsonl` (9) · `runs/p1a_build_summary.json` ·
`runs/trajectories/` (empty — no rollouts) · `logs/` · `provenance.txt`.
