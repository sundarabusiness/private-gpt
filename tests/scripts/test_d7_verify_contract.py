import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "d7_verify_contract.py"
SPEC = importlib.util.spec_from_file_location("d7_verify_contract", SCRIPT_PATH)
assert SPEC is not None
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_d7_contract_verifier_passes_for_repo() -> None:
    root = Path(__file__).parents[2]
    report = MODULE.verify(root)
    assert report["passed"]

