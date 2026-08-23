import importlib


def test_tau_adapter_imports_without_tau_installed():
    module = importlib.import_module("art_p0.tau_adapter")
    assert hasattr(module, "BudgetEnforcingAgent")
