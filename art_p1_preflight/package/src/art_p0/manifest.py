"""Frozen harness identity (P0.2 fix for P0.1 Observation O2).

P0.1's harness hash covered only ``agent_llm`` / ``agent_llm_args`` / wrapper /
overflow policy.  A change in the domain policy text, the system prompt, the
user model, the tool schema, or the pinned benchmark revision would NOT change
the hash -- so "frozen harness identity" was incomplete.

``FrozenHarnessManifest`` captures the full identity of the *measurement
apparatus*.  Its ``manifest_hash()`` is the SHA-256 of a canonical dict of the
harness-identity fields **only**.

Design principle (required by the task):

    harness identity  !=  experimental-condition identity

* Changing the *resource budget* (or seed, or task id) must NOT change the
  harness hash -- these select *which measurement* you take with a fixed
  apparatus, not the apparatus itself.  They live in :class:`ExperimentCondition`.
* Changing the system prompt, policy text, tool schema, models, or benchmark
  revision MUST change the harness hash -- these change the apparatus, so two
  such runs are not the same experimental setup and must not be pooled.

Why each experiment-identity field is excluded from the harness hash:

* ``resource_budget`` -- the P0 experiment *varies* budget across runs of one
  fixed harness (I5 requires all budgets share one harness hash).  Folding it
  in would make every budget a different "harness" and break I5.
* ``seed`` -- a re-randomization of the *same* apparatus; runs at different
  seeds are repeated measurements of one condition family, not different rigs.
* ``task_id`` -- selects the stimulus, not the apparatus; the same harness
  measures many tasks.  Pooling across tasks is a downstream analysis choice,
  not a harness-identity change.

All three are still recorded (in :class:`ExperimentCondition`) so a run is fully
reproducible; they are simply hashed separately from harness identity.
"""
from __future__ import annotations

import dataclasses
import hashlib
from dataclasses import dataclass, field
from typing import Any, Optional

from .hashing import canonical_json


def _sha256_text(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FrozenHarnessManifest:
    """Complete, canonical identity of a frozen measurement harness.

    Prompt/policy texts are stored as SHA-256 hashes (they can be large and are
    reproducible from the pinned revision); model identity, args, permissions,
    and revisions are stored verbatim.  Every field here is part of harness
    identity: change any one and ``manifest_hash()`` changes.
    """

    agent_model: str
    agent_model_args: dict[str, Any] = field(default_factory=dict)
    reasoning_effort: Optional[str] = None
    agent_system_prompt_hash: Optional[str] = None
    agent_policy_prompt_hash: Optional[str] = None
    domain_policy_text_hash: Optional[str] = None
    wrapper_class: str = "art_p0.BudgetEnforcingAgent"
    budget_overflow_policy: str = "atomic_raise"
    tool_schema_hash: Optional[str] = None
    tool_permissions: dict[str, str] = field(default_factory=dict)
    user_model: Optional[str] = None
    user_model_args: dict[str, Any] = field(default_factory=dict)
    max_steps: Optional[int] = None
    benchmark_runtime_commit: Optional[str] = None
    verified_dataset_commit: Optional[str] = None
    # Free-form namespace for additional apparatus identity (e.g. domain name,
    # evaluation_type). Included in the hash.
    extra: dict[str, Any] = field(default_factory=dict)

    def to_canonical_dict(self) -> dict[str, Any]:
        """Harness-identity dict used for hashing (deterministic ordering)."""
        return dataclasses.asdict(self)

    def manifest_hash(self) -> str:
        """SHA-256 over the canonical harness-identity dict."""
        payload = canonical_json(self.to_canonical_dict()).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    # Convenience constructors ------------------------------------------------
    @classmethod
    def from_texts(
        cls,
        *,
        agent_model: str,
        agent_model_args: Optional[dict] = None,
        reasoning_effort: Optional[str] = None,
        agent_system_prompt: Optional[str] = None,
        agent_policy_prompt: Optional[str] = None,
        domain_policy_text: Optional[str] = None,
        wrapper_class: str = "art_p0.BudgetEnforcingAgent",
        budget_overflow_policy: str = "atomic_raise",
        tool_schema: Any = None,
        tool_permissions: Optional[dict[str, str]] = None,
        user_model: Optional[str] = None,
        user_model_args: Optional[dict] = None,
        max_steps: Optional[int] = None,
        benchmark_runtime_commit: Optional[str] = None,
        verified_dataset_commit: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> "FrozenHarnessManifest":
        """Build a manifest, hashing prompt/policy/tool-schema texts for you."""
        tool_schema_hash = None
        if tool_schema is not None:
            tool_schema_hash = _sha256_text(canonical_json(tool_schema))
        return cls(
            agent_model=agent_model,
            agent_model_args=dict(agent_model_args or {}),
            reasoning_effort=reasoning_effort,
            agent_system_prompt_hash=_sha256_text(agent_system_prompt),
            agent_policy_prompt_hash=_sha256_text(agent_policy_prompt),
            domain_policy_text_hash=_sha256_text(domain_policy_text),
            wrapper_class=wrapper_class,
            budget_overflow_policy=budget_overflow_policy,
            tool_schema_hash=tool_schema_hash,
            tool_permissions=dict(tool_permissions or {}),
            user_model=user_model,
            user_model_args=dict(user_model_args or {}),
            max_steps=max_steps,
            benchmark_runtime_commit=benchmark_runtime_commit,
            verified_dataset_commit=verified_dataset_commit,
            extra=dict(extra or {}),
        )


@dataclass(frozen=True)
class ExperimentCondition:
    """Identity of a single experimental condition under a fixed harness.

    Recorded for full reproducibility but hashed *separately* from harness
    identity (see module docstring).  ``resource_budget`` varying while
    ``harness_hash`` stays constant is exactly P0's I5 invariant.
    """

    harness_hash: str
    task_id: str
    seed: Optional[int] = None
    resource_budget: Optional[int] = None

    def condition_hash(self) -> str:
        payload = canonical_json(dataclasses.asdict(self)).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def build_manifest_from_tau2_env(
    env: Any,
    *,
    agent_model: str,
    agent_system_prompt: Optional[str] = None,
    agent_policy_prompt: Optional[str] = None,
    agent_model_args: Optional[dict] = None,
    reasoning_effort: Optional[str] = None,
    wrapper_class: str = "art_p0.BudgetEnforcingAgent",
    user_model: Optional[str] = None,
    user_model_args: Optional[dict] = None,
    max_steps: Optional[int] = None,
    benchmark_runtime_commit: Optional[str] = None,
    verified_dataset_commit: Optional[str] = None,
    extra: Optional[dict] = None,
) -> FrozenHarnessManifest:
    """Build a manifest from a constructed tau2 ``Environment``.

    Extracts the domain policy text, the tool JSON schema, and per-tool
    permission (read/write/generic/think) from the live environment so the
    apparatus identity reflects the actual runtime, not a hand-copied string.
    tau2 is imported lazily by the caller (env is already constructed).
    """
    domain_policy_text = None
    getp = getattr(env, "get_policy", None)
    if callable(getp):
        try:
            domain_policy_text = getp()
        except Exception:  # pragma: no cover - defensive
            domain_policy_text = None

    tool_schema: Any = None
    tool_permissions: dict[str, str] = {}
    try:
        tools = []
        if callable(getattr(env, "get_tools", None)):
            tools.extend(env.get_tools() or [])
        if callable(getattr(env, "get_user_tools", None)):
            tools.extend(env.get_user_tools() or [])
        schema_items = []
        for t in tools:
            name = getattr(t, "name", None)
            # Tool type / permission
            ttype = getattr(t, "type", None)
            perm = getattr(ttype, "value", ttype)
            if name is not None and perm is not None:
                tool_permissions[str(name)] = str(perm)
            # A stable schema fingerprint: name + params, if exposed.
            params = getattr(t, "params", None) or getattr(t, "parameters", None)
            schema_items.append(
                {"name": name, "params": params if isinstance(params, (dict, list)) else str(params)}
            )
        tool_schema = sorted(schema_items, key=lambda d: str(d.get("name")))
    except Exception:  # pragma: no cover - defensive
        tool_schema = None

    return FrozenHarnessManifest.from_texts(
        agent_model=agent_model,
        agent_model_args=agent_model_args,
        reasoning_effort=reasoning_effort,
        agent_system_prompt=agent_system_prompt,
        agent_policy_prompt=agent_policy_prompt,
        domain_policy_text=domain_policy_text,
        wrapper_class=wrapper_class,
        tool_schema=tool_schema,
        tool_permissions=tool_permissions,
        user_model=user_model,
        user_model_args=user_model_args,
        max_steps=max_steps,
        benchmark_runtime_commit=benchmark_runtime_commit,
        verified_dataset_commit=verified_dataset_commit,
        extra=extra,
    )
