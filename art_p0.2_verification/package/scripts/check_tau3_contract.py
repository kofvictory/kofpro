#!/usr/bin/env python3
"""No-LLM compatibility check against an installed current τ³/tau2 package."""
from __future__ import annotations

import inspect
import json
import sys


def main() -> int:
    report = {"ok": True, "checks": {}}
    try:
        from tau2.agent import LLMAgent
        from tau2.agent.base_agent import HalfDuplexAgent
        from tau2.orchestrator.orchestrator import Orchestrator
        from tau2.runner import build_environment, build_user, get_tasks, run_simulation
    except Exception as exc:
        print(json.dumps({"ok": False, "import_error": repr(exc)}, indent=2))
        return 2

    checks = report["checks"]
    checks["half_duplex_methods"] = all(
        hasattr(HalfDuplexAgent, name)
        for name in ("get_init_state", "generate_next_message")
    )
    checks["runner_symbols"] = all(
        callable(x)
        for x in (build_environment, build_user, get_tasks, run_simulation)
    )
    checks["orchestrator_has_agent_state"] = "agent" in inspect.signature(
        Orchestrator
    ).parameters
    checks["llm_agent_ctor"] = all(
        p in inspect.signature(LLMAgent).parameters
        for p in ("tools", "domain_policy", "llm", "llm_args")
    )

    try:
        tasks = get_tasks("mock", task_ids=["create_task_1"])
        env = build_environment("mock")
        checks["mock_task"] = len(tasks) == 1 and str(tasks[0].id) == "create_task_1"
        checks["mock_env"] = callable(getattr(env, "get_tools", None)) and callable(
            getattr(env, "get_policy", None)
        )
    except Exception as exc:
        checks["mock_task"] = False
        checks["mock_env"] = False
        report["mock_error"] = repr(exc)

    report["ok"] = all(checks.values())
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    sys.exit(main())
