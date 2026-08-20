"""U1, U2 -- initialized-environment-state hash stability and sensitivity.

Requires tau2 (telecom domain). Skipped automatically if tau2 is absent.
"""
import pytest

pytest.importorskip("tau2")

from tau2.runner import get_tasks  # noqa: E402
from tau2.registry import registry  # noqa: E402

from art_p0.state_hash import (  # noqa: E402
    environment_initial_state_hash,
    initialize_environment,
    task_initial_state_hash,
)

DOMAIN = "telecom"


def _tasks():
    return {t.id: t for t in get_tasks(DOMAIN)}


def test_u1_env_hash_stable_same_task_same_runtime():
    """U1: same task + same runtime + same init -> identical env hash."""
    tasks = _tasks()
    tid = next(iter(tasks))
    task = tasks[tid]
    ctor = registry.get_env_constructor(DOMAIN)
    h1 = environment_initial_state_hash(
        initialize_environment(ctor, task), domain=DOMAIN
    )
    h2 = environment_initial_state_hash(
        initialize_environment(ctor, task), domain=DOMAIN
    )
    assert h1 == h2
    assert len(h1) == 64
    # task hash also stable
    assert task_initial_state_hash(task) == task_initial_state_hash(task)


def test_u2_env_hash_sensitive_to_semantic_db_change():
    """U2: change one semantic DB field -> different env hash."""
    tasks = _tasks()
    task = next(iter(tasks.values()))
    ctor = registry.get_env_constructor(DOMAIN)
    env = initialize_environment(ctor, task)
    before = environment_initial_state_hash(env, domain=DOMAIN)

    # Mutate exactly one semantic field of the (user) device state, then rehash.
    mutated = False
    for tool_name in ("toggle_airplane_mode", "toggle_data", "toggle_roaming"):
        if env._has_tool(tool_name):
            from tau2.data_model.message import ToolCall

            env.get_response(ToolCall(id="m", name=tool_name, arguments={}, requestor="user"))
            mutated = True
            break
    assert mutated, "expected at least one togglable device tool in telecom"
    after = environment_initial_state_hash(env, domain=DOMAIN)
    assert before != after


def test_u2b_different_tasks_differ():
    """Two tasks with different initial device state hash differently."""
    tasks = list(_tasks().values())
    ctor = registry.get_env_constructor(DOMAIN)
    hashes = {
        environment_initial_state_hash(initialize_environment(ctor, t), domain=DOMAIN)
        for t in tasks[:40]
    }
    # Not all 40 telecom tasks share one initial device state.
    assert len(hashes) > 1
