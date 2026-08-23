"""P1 fixed harnesses: h0 (nominal), h1 (budget-aware), h2 (+plan-and-verify).

All three share the same agent model, reasoning effort, tools, tool
permissions, domain policy, max steps, user simulator, execution environment,
and benchmark commits.  ONLY the intended harness policy differs:

* **h0 nominal**       -- standard tau LLM agent under the P0.1-verified
  ``BudgetEnforcingAgent``.  The hard budget is enforced, but the remaining
  budget is NOT proactively exposed to the model.
* **h1 budget-aware**  -- identical to h0 plus a per-turn, concise statement of
  the remaining hard tool-call budget.  No planning / verification / domain
  advice is added.  ``h1 - h0`` isolates budget awareness.
* **h2 +plan-verify**  -- h1 plus a generic (task-agnostic) plan-and-verify
  instruction in the system prompt.  ``h2 - h1`` isolates plan-and-verify.

Budget enforcement is delegated to the verified P0.1 wrapper; h1/h2 use a thin
subclass that only *informs* the inner agent of the remaining budget before each
turn and otherwise calls the parent unchanged -- the atomic-overflow semantics
(I2/I7) are preserved exactly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .tau_adapter import BudgetEnforcingAgent

# --- exact intervention texts (frozen) --------------------------------------
BUDGET_AWARE_TEMPLATE = (
    "Hard tool-call budget remaining: {remaining}.\n"
    "Use the available calls carefully. You may stop before exhausting the budget."
)

PLAN_VERIFY_SUFFIX = (
    "\n\n"
    "Before taking consequential actions, identify the task goal, the "
    "information required to complete it, and the likely state-changing actions.\n"
    "Before an irreversible or state-changing tool action, verify that its "
    "prerequisites are satisfied.\n"
    "Do not reveal private chain-of-thought. Only produce the tool calls and "
    "user-facing responses needed to perform the task."
)


@dataclass(frozen=True)
class HarnessSpec:
    harness_id: str
    expose_budget: bool
    plan_verify: bool
    wrapper_class: str
    description: str


HARNESS_SPECS: dict[str, HarnessSpec] = {
    "h0": HarnessSpec("h0", False, False, "art_p0.BudgetEnforcingAgent", "nominal"),
    "h1": HarnessSpec(
        "h1", True, False, "art_p0.harnesses.BudgetAwareEnforcingAgent",
        "budget awareness",
    ),
    "h2": HarnessSpec(
        "h2", True, True, "art_p0.harnesses.BudgetAwareEnforcingAgent",
        "budget awareness + plan-and-verify",
    ),
}
HARNESS_IDS = ("h0", "h1", "h2")


# --- prompt policy (used for BOTH runtime agents and manifest hashing) -------
def _tau2_prompt_parts():
    from tau2.agent.llm_agent import AGENT_INSTRUCTION, SYSTEM_PROMPT

    return AGENT_INSTRUCTION, SYSTEM_PROMPT


def agent_instruction_for(harness_id: str) -> str:
    """The <instructions> block for a harness (base, or base+plan-verify)."""
    agent_instruction, _ = _tau2_prompt_parts()
    spec = HARNESS_SPECS[harness_id]
    return agent_instruction + (PLAN_VERIFY_SUFFIX if spec.plan_verify else "")


def system_prompt_policy(harness_id: str, domain_policy: str) -> str:
    """Canonical, frozen representation of a harness's agent prompt policy.

    Used for ``agent_system_prompt_hash`` in the manifest, so that h0, h1 and h2
    hash differently.  For h1/h2 the per-turn budget-exposure template (with its
    ``{remaining}`` placeholder) is appended to represent the exposure policy;
    the numeric value is filled in per turn at run time, not frozen here.
    """
    _, system_prompt = _tau2_prompt_parts()
    base = system_prompt.format(
        agent_instruction=agent_instruction_for(harness_id),
        domain_policy=domain_policy,
    )
    spec = HARNESS_SPECS[harness_id]
    if spec.expose_budget:
        base = base + "\n\n[PER-TURN BUDGET EXPOSURE]\n" + BUDGET_AWARE_TEMPLATE
    return base


def agent_policy_prompt_for(harness_id: str) -> str:
    """The behavioral instruction policy (excludes the domain policy text)."""
    return agent_instruction_for(harness_id) + (
        "\n\n[PER-TURN BUDGET EXPOSURE]\n" + BUDGET_AWARE_TEMPLATE
        if HARNESS_SPECS[harness_id].expose_budget
        else ""
    )


# --- runtime agents ----------------------------------------------------------
_AGENT_CACHE: dict[str, Any] = {}


def _budget_aware_agent_class():
    """Build (and cache) the BudgetAwareAgent subclass of tau2's LLMAgent."""
    if "BudgetAwareAgent" in _AGENT_CACHE:
        return _AGENT_CACHE["BudgetAwareAgent"]

    from tau2.agent.llm_agent import LLMAgent
    from tau2.data_model.message import MultiToolMessage, SystemMessage, UserMessage
    from tau2.utils.llm_utils import generate

    class BudgetAwareAgent(LLMAgent):
        """LLMAgent that injects the remaining hard budget each turn.

        Identical to ``LLMAgent`` except that (a) for plan_verify it adds the
        generic plan-and-verify suffix to the frozen system prompt, and (b) each
        turn it appends a concise "remaining budget" line to the system message
        actually sent to the model. The remaining value is provided by the
        enforcing wrapper via ``set_remaining_budget`` before each turn.
        """

        def __init__(self, tools, domain_policy, llm, llm_args=None, *, plan_verify=False):
            super().__init__(tools=tools, domain_policy=domain_policy, llm=llm, llm_args=llm_args)
            self._plan_verify = bool(plan_verify)
            self._remaining: Optional[int] = None

        @property
        def system_prompt(self) -> str:  # frozen part (plan-verify only)
            from tau2.agent.llm_agent import SYSTEM_PROMPT

            hid = "h2" if self._plan_verify else "h1"
            return SYSTEM_PROMPT.format(
                agent_instruction=agent_instruction_for(hid),
                domain_policy=self.domain_policy,
            )

        def set_remaining_budget(self, remaining: int) -> None:
            self._remaining = remaining

        def _generate_next_message(self, message, state):
            if isinstance(message, UserMessage) and getattr(message, "is_audio", False):
                raise ValueError("User message cannot be audio. Use VoiceLLMAgent instead.")
            if isinstance(message, MultiToolMessage):
                state.messages.extend(message.tool_messages)
            elif message is not None:
                state.messages.append(message)

            base_sys = (
                state.system_messages[0].content
                if state.system_messages
                else self.system_prompt
            )
            if self._remaining is not None:
                base_sys = base_sys + "\n\n" + BUDGET_AWARE_TEMPLATE.format(
                    remaining=self._remaining
                )
            messages = [SystemMessage(role="system", content=base_sys)] + state.messages
            return generate(
                model=self.llm,
                tools=self.tools,
                messages=messages,
                call_name="agent_response",
                **self.llm_args,
            )

    _AGENT_CACHE["BudgetAwareAgent"] = BudgetAwareAgent
    return BudgetAwareAgent


class BudgetAwareEnforcingAgent(BudgetEnforcingAgent):
    """Hard-budget wrapper that also *informs* the inner agent of the remaining
    budget before each turn. All enforcement (atomic overflow -> BudgetExceeded)
    is inherited unchanged from the P0.1-verified ``BudgetEnforcingAgent``.
    """

    def generate_next_message(self, message, state):
        remaining = self.tool_budget - state.budget_used
        setter = getattr(self.inner_agent, "set_remaining_budget", None)
        if callable(setter):
            setter(remaining)
        return super().generate_next_message(message, state)


def build_inner_agent(harness_id: str, *, tools, domain_policy, llm, llm_args=None):
    """Construct the inner tau2 agent for a harness (h0 = plain LLMAgent)."""
    from tau2.agent.llm_agent import LLMAgent

    if harness_id == "h0":
        return LLMAgent(tools=tools, domain_policy=domain_policy, llm=llm, llm_args=llm_args)
    cls = _budget_aware_agent_class()
    return cls(
        tools=tools,
        domain_policy=domain_policy,
        llm=llm,
        llm_args=llm_args,
        plan_verify=(harness_id == "h2"),
    )


def wrap_agent(inner_agent, harness_id: str, tool_budget: int):
    """Apply the appropriate hard-budget wrapper for a harness."""
    if harness_id == "h0":
        return BudgetEnforcingAgent(inner_agent=inner_agent, tool_budget=tool_budget)
    return BudgetAwareEnforcingAgent(inner_agent=inner_agent, tool_budget=tool_budget)


def build_harness_manifest(
    env: Any,
    harness_id: str,
    *,
    agent_model: str,
    reasoning_effort: str,
    user_model: str,
    max_steps: int,
    benchmark_runtime_commit: str,
    verified_dataset_commit: str,
    agent_model_args: Optional[dict] = None,
    user_model_args: Optional[dict] = None,
):
    """Build a FrozenHarnessManifest for one harness from a live tau2 env."""
    from .manifest import build_manifest_from_tau2_env

    domain_policy = env.get_policy() if callable(getattr(env, "get_policy", None)) else None
    spec = HARNESS_SPECS[harness_id]
    return build_manifest_from_tau2_env(
        env,
        agent_model=agent_model,
        agent_model_args=agent_model_args or {},
        reasoning_effort=reasoning_effort,
        agent_system_prompt=system_prompt_policy(harness_id, domain_policy or ""),
        agent_policy_prompt=agent_policy_prompt_for(harness_id),
        wrapper_class=spec.wrapper_class,
        user_model=user_model,
        user_model_args=user_model_args or {},
        max_steps=max_steps,
        benchmark_runtime_commit=benchmark_runtime_commit,
        verified_dataset_commit=verified_dataset_commit,
        extra={
            "harness_id": harness_id,
            "expose_budget": spec.expose_budget,
            "plan_verify": spec.plan_verify,
            "domain": env.get_domain_name() if callable(getattr(env, "get_domain_name", None)) else "telecom",
            "evaluation_type": "ALL",
        },
    )
