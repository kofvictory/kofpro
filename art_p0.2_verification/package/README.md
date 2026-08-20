# ART P0 Instrumentation v0.2

Auditable instrumentation for the first calibration stage of the Agent Capability
Elicitation Measurement project.

## Components

- `ToolCallBudget`: hard atomic tool-call ceiling; never silently truncates a tool-call batch.
- `BudgetEnforcingAgent`: thin current-τ³ half-duplex wrapper.
- `RunLedger`: append-only JSONL accounting for availability, consumption, outcomes and run identity.
- `TrajectoryStore`: one loss-tolerant JSON trajectory artifact per run.
- `harness_hash`: canonical SHA-256 identity for frozen harness configurations.
- `TaskValidator`: five-probe task audit (`gold`, `noop`, `omission`, `alternative`, `policy`).
- `tau3_runtime.run_tau3_once`: current public power-user API integration.
- `tau3_mock_matrix.py`: budgets `1 2 4` with post-run invariant checks.
- `check_tau3_contract.py`: no-LLM compatibility check against an installed tau2/τ³ checkout.

## Scientific invariants

1. **Availability is not consumption.** `tool_budget_limit` and `tool_calls_used` are separate fields.
2. **No hidden policy mutation.** A batch that would exceed budget is rejected atomically rather than truncated.
3. **Nested budgets.** A trajectory feasible at budget `B` remains feasible at any larger budget if the underlying agent chooses the same actions.
4. **Frozen harness identity.** Prompt/config/policy changes produce a different SHA-256 hash.
5. **Append-only run accounting.** One JSON object per completed run.
6. **Fresh environment per experimental unit.** Each run constructs a new environment; the orchestrator then reapplies the task initial state.
7. **Trajectory persistence.** Every run writes a separate JSON diagnostic artifact.
8. **Task validity is adversarial.** A task is admitted only when all five validation probes pass.

## Local P0 tests (no LLM key)

```bash
python -m pip install -e '.[dev]'
pytest -q
```

## P0.1 inside a pinned τ³ checkout

Install this package in the same Python environment as τ³/tau2, then first run the
zero-LLM contract check:

```bash
python scripts/check_tau3_contract.py
```

Then run a single smoke task:

```bash
python scripts/tau3_mock_smoke.py \
  --agent-llm openai/gpt-4.1-mini \
  --user-llm openai/gpt-4.1-mini \
  --budget 4 --seed 42
```

Finally run the fixed P0 matrix:

```bash
python scripts/tau3_mock_matrix.py \
  --agent-llm openai/gpt-4.1-mini \
  --user-llm openai/gpt-4.1-mini \
  --budgets 1 2 4 --seed 42
```

The matrix exits non-zero if the harness/task/seed/initial-state fingerprint changes,
if a fresh environment object is not constructed for each experimental unit, if
consumption exceeds availability, if budget overflow is mislabeled as success, or if
trajectory persistence is missing.

## Reproducibility requirement

Before any scientific rollout, record the pinned benchmark revision:

```bash
git -C /path/to/tau2-bench rev-parse HEAD
```

Store that SHA in the experiment manifest.  Do not treat runs across different τ³
revisions as the same experimental condition.

## Current limitation

This artifact was contract-tested against the public current τ³ API and unit-tested
without the benchmark package.  The working container cannot resolve GitHub, so the
actual τ³ package cannot be installed here.  End-to-end P0.1 remains a run to execute
inside a pinned τ³ environment before enabling the Telecom validation pipeline.
