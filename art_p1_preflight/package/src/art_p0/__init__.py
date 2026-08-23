"""ART P0 instrumentation package."""

from .budget import BudgetExceeded, BudgetState, ToolCallBudget
from .hashing import harness_hash
from .ledger import RunLedger, RunRecord
from .manifest import ExperimentCondition, FrozenHarnessManifest, build_manifest_from_tau2_env
from .state_hash import (
    compute_state_hashes,
    environment_initial_state_hash,
    initialize_environment,
    task_initial_state_hash,
)
from .tau3_runtime import Tau3RunSpec, check_matrix_invariants, run_tau3_once
from .trajectory import TrajectoryStore
from .validator import TaskValidator

__all__ = [
    "BudgetExceeded",
    "BudgetState",
    "ToolCallBudget",
    "RunLedger",
    "RunRecord",
    "TaskValidator",
    "TrajectoryStore",
    "Tau3RunSpec",
    "run_tau3_once",
    "check_matrix_invariants",
    "harness_hash",
    # P0.2 O1
    "task_initial_state_hash",
    "environment_initial_state_hash",
    "initialize_environment",
    "compute_state_hashes",
    # P0.2 O2
    "FrozenHarnessManifest",
    "ExperimentCondition",
    "build_manifest_from_tau2_env",
]

# P1 modules are imported lazily by scripts/tests to keep the base package light.

