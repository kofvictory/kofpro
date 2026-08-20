from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Any


def _normalize(obj: Any) -> Any:
    if dataclasses.is_dataclass(obj):
        return _normalize(dataclasses.asdict(obj))
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): _normalize(v) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))}
    if isinstance(obj, (list, tuple)):
        return [_normalize(v) for v in obj]
    if isinstance(obj, set):
        return sorted((_normalize(v) for v in obj), key=repr)
    if hasattr(obj, "model_dump"):
        return _normalize(obj.model_dump(mode="json"))
    return obj


def canonical_json(obj: Any) -> str:
    """Stable JSON representation used for preregistered harness identity."""
    return json.dumps(
        _normalize(obj),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def harness_hash(config: Any) -> str:
    """SHA-256 of a canonicalized harness configuration."""
    payload = canonical_json(config).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
