"""Initial-state fingerprinting (P0.2 fix for P0.1 Observation O1).

P0.1 hashed only ``task.initial_state``.  For the mock domain that field is
``None`` for every task, so every run shared ``sha256("null")`` and the
initial-state-equality invariant (I3) held only *trivially*.  The true initial
DB/state produced by ``Environment.set_state(...)`` was never captured.

This module adds two *separate*, canonical, deterministic fingerprints:

* ``task_initial_state_hash``          -- the DECLARED task initial state
  (``initialization_data`` / ``initialization_actions`` / ``message_history``).
* ``environment_initial_state_hash``   -- the ACTUAL environment state after
  ``Orchestrator``-equivalent initialization (fresh env + ``set_state``), i.e.
  the agent DB + user DB + domain identity.

Both use canonical JSON serialization with deterministic key ordering, are
stable across repeated identical runs, change when a semantic DB field changes,
and deliberately exclude non-semantic fields (Python object ids, wall-clock
timestamps, memory addresses).  They are computed independently of the P0.1
budget path, so the verified budget semantics are untouched.
"""
from __future__ import annotations

import hashlib
from typing import Any, Callable, Optional

from .hashing import canonical_json


# Keys that are never part of the *semantic* environment state.  If a DB model
# ever surfaces such a field we drop it before hashing so that two runs that
# differ only by wall-clock/object identity still hash identically.
_NON_SEMANTIC_KEYS = frozenset(
    {
        "timestamp",
        "created_at",
        "updated_at",
        "started_at",
        "finished_at",
        "_object_id",
        "object_id",
        "id_",
    }
)


def _strip_non_semantic(obj: Any) -> Any:
    """Recursively drop known non-semantic keys (timestamps, object ids)."""
    if isinstance(obj, dict):
        return {
            k: _strip_non_semantic(v)
            for k, v in obj.items()
            if k not in _NON_SEMANTIC_KEYS
        }
    if isinstance(obj, (list, tuple)):
        return [_strip_non_semantic(v) for v in obj]
    return obj


def _sha256_of(obj: Any) -> str:
    payload = canonical_json(_strip_non_semantic(obj)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _dump(model: Any) -> Any:
    """Best-effort canonical dict for a (pydantic or plain) DB object."""
    if model is None:
        return None
    if hasattr(model, "model_dump"):
        try:
            return model.model_dump(mode="json")
        except TypeError:
            return model.model_dump()
    if hasattr(model, "dict"):
        try:
            return model.dict()
        except Exception:  # pragma: no cover - defensive
            pass
    return model


def task_initial_state_hash(task: Any) -> str:
    """Canonical SHA-256 of the task's declared initial state.

    Captures ``initialization_data``, ``initialization_actions`` and
    ``message_history``.  ``None`` initial states still hash deterministically
    (this is the P0.1 behavior, retained for backwards comparison), but is now
    complemented by :func:`environment_initial_state_hash`.
    """
    istate = getattr(task, "initial_state", None)
    return _sha256_of(_dump(istate))


def _extract_db(env: Any, attr: str) -> Any:
    toolkit = getattr(env, attr, None)
    if toolkit is None:
        return None
    return _dump(getattr(toolkit, "db", None))


def environment_initial_state_hash(env: Any, *, domain: Optional[str] = None) -> str:
    """Canonical SHA-256 of the *initialized* environment state.

    Snapshot = {domain, agent_db, user_db}.  The env must already have had
    ``set_state(...)`` applied (see :func:`initialize_environment`).  Two envs
    with different DB contents hash differently; two identically-initialized
    envs hash identically regardless of object identity.
    """
    if domain is None:
        # tau2 environments expose get_domain_name(); fall back gracefully.
        getter = getattr(env, "get_domain_name", None)
        domain = getter() if callable(getter) else getattr(env, "domain_name", None)
    snapshot = {
        "domain": domain,
        "agent_db": _extract_db(env, "tools"),
        "user_db": _extract_db(env, "user_tools"),
    }
    return _sha256_of(snapshot)


def initialize_environment(
    env_constructor: Callable[..., Any],
    task: Any,
    *,
    solo_mode: bool = False,
    env_kwargs: Optional[dict] = None,
) -> Any:
    """Construct a fresh environment and apply the task's initial state.

    Mirrors ``Orchestrator.initialize()`` reset semantics: a new environment
    object, then ``set_state`` with the task's declared initialization.  Returns
    the initialized environment (a *new* object every call -- fresh-env I4).
    """
    env = env_constructor(solo_mode=solo_mode, **(env_kwargs or {}))
    istate = getattr(task, "initial_state", None)
    env.set_state(
        initialization_data=getattr(istate, "initialization_data", None)
        if istate is not None
        else None,
        initialization_actions=getattr(istate, "initialization_actions", None)
        if istate is not None
        else None,
        message_history=[],
    )
    return env


def compute_state_hashes(
    domain: str,
    task: Any,
    env_constructor: Optional[Callable[..., Any]] = None,
    *,
    solo_mode: bool = False,
    env_kwargs: Optional[dict] = None,
) -> dict[str, str]:
    """Return both fingerprints for a task.

    ``environment_initial_state_hash`` is included only when an
    ``env_constructor`` is supplied (the caller has the benchmark installed).
    """
    out = {"task_initial_state_hash": task_initial_state_hash(task)}
    if env_constructor is not None:
        env = initialize_environment(
            env_constructor, task, solo_mode=solo_mode, env_kwargs=env_kwargs
        )
        out["environment_initial_state_hash"] = environment_initial_state_hash(
            env, domain=domain
        )
    return out
