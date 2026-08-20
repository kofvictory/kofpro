"""Loss-tolerant, auditable trajectory persistence.

The benchmark's Pydantic message models can change across releases.  We therefore
prefer their JSON/model dump APIs when available and fall back to a restricted
plain-Python serializer.  Persistence is diagnostic only; benchmark scoring
continues to use tau2's native objects.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
from pathlib import Path
from typing import Any


def to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if hasattr(value, "model_dump"):
        try:
            return to_jsonable(value.model_dump(mode="json"))
        except TypeError:
            return to_jsonable(value.model_dump())
    if hasattr(value, "dict"):
        try:
            return to_jsonable(value.dict())
        except Exception:
            pass
    if hasattr(value, "value") and isinstance(getattr(value, "value"), (str, int)):
        return getattr(value, "value")
    return {"__class__": value.__class__.__name__, "repr": repr(value)}


class TrajectoryStore:
    """One JSON file per run, written atomically by rename."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, run_id: str) -> Path:
        return self.root / f"{run_id}.json"

    def write(self, run_id: str, payload: dict[str, Any]) -> Path:
        path = self.path_for(run_id)
        tmp = path.with_suffix(".json.tmp")
        text = json.dumps(
            to_jsonable(payload),
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
            indent=2,
        )
        tmp.write_text(text + "\n", encoding="utf-8")
        tmp.replace(path)
        return path
