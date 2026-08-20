from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock
from typing import Any, Optional
import uuid


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RunRecord:
    run_id: str
    task_id: str
    harness_id: str
    harness_hash: str
    resource_interface_id: str
    seed: Optional[int]
    tool_budget_limit: int
    tool_calls_used: int = 0
    turns_used: int = 0
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    wall_seconds: Optional[float] = None
    success_official: Optional[bool] = None
    success_strict: Optional[bool] = None
    termination_reason: Optional[str] = None
    budget_exceeded: bool = False
    # P0.2 (Observation O1): separate, canonical initial-state fingerprints.
    # Optional so all pre-existing P0.1 ledgers and records remain valid.
    task_initial_state_hash: Optional[str] = None
    environment_initial_state_hash: Optional[str] = None
    started_at: str = field(default_factory=_utc_now)
    finished_at: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def new(
        cls,
        *,
        task_id: str,
        harness_id: str,
        harness_hash: str,
        resource_interface_id: str,
        seed: Optional[int],
        tool_budget_limit: int,
        metadata: Optional[dict[str, Any]] = None,
    ) -> "RunRecord":
        return cls(
            run_id=str(uuid.uuid4()),
            task_id=task_id,
            harness_id=harness_id,
            harness_hash=harness_hash,
            resource_interface_id=resource_interface_id,
            seed=seed,
            tool_budget_limit=tool_budget_limit,
            metadata=dict(metadata or {}),
        )

    def finish(self) -> None:
        self.finished_at = _utc_now()


class RunLedger:
    """Append-only JSONL ledger with a process-local write lock."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def append(self, record: RunRecord) -> None:
        if record.finished_at is None:
            record.finish()
        line = json.dumps(asdict(record), ensure_ascii=False, sort_keys=True, allow_nan=False)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()

    def read_all(self) -> list[RunRecord]:
        if not self.path.exists():
            return []
        out: list[RunRecord] = []
        with self.path.open("r", encoding="utf-8") as f:
            for raw in f:
                if raw.strip():
                    out.append(RunRecord(**json.loads(raw)))
        return out
