import importlib.util
from pathlib import Path
from typing import Any

import pytest
import requests


SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "d7_privategpt_retriever.py"
SPEC = importlib.util.spec_from_file_location("d7_privategpt_retriever", SCRIPT_PATH)
assert SPEC is not None
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_retriever_client_fails_closed_on_network_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_post(*args: Any, **kwargs: Any) -> None:
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr(MODULE.requests, "post", fail_post)

    with pytest.raises(MODULE.PrivateGptSubstrateError):
        MODULE.retrieve(
            "http://127.0.0.1:9",
            MODULE.RetrieverRequest(query="B12345_001A", parcel_id="B12345_001A"),
        )


def test_retriever_client_default_base_url_is_privategpt_port() -> None:
    assert MODULE.DEFAULT_BASE_URL == "http://127.0.0.1:8000"
