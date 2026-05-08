import importlib.util
from pathlib import Path
from typing import Any

import pytest


SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "d7_adversarial_probe.py"
SPEC = importlib.util.spec_from_file_location("d7_adversarial_probe", SCRIPT_PATH)
assert SPEC is not None
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_adversarial_probe_passes_when_all_fabrications_are_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def empty_retrieve(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"status": "EMPTY", "empty_reason": "no_source_match"}

    monkeypatch.setattr(MODULE, "retrieve", empty_retrieve)

    report = MODULE.run_probes(
        "http://127.0.0.1:8000",
        MODULE.default_probes(),
        required_pass_rate=0.9,
    )

    assert report["passed"]
    assert report["pass_rate"] == 1.0


def test_adversarial_probe_fails_below_required_pass_rate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"count": 0}

    def mixed_retrieve(*args: Any, **kwargs: Any) -> dict[str, Any]:
        calls["count"] += 1
        if calls["count"] <= 2:
            return {"status": "FOUND"}
        return {"status": "EMPTY", "empty_reason": "no_source_match"}

    monkeypatch.setattr(MODULE, "retrieve", mixed_retrieve)

    report = MODULE.run_probes(
        "http://127.0.0.1:8000",
        MODULE.default_probes(),
        required_pass_rate=0.9,
    )

    assert not report["passed"]
    assert report["pass_rate"] == 0.8
