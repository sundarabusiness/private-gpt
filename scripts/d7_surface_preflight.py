#!/usr/bin/env python3
"""Preflight checks for bringing D7 PrivateGPT live on an ARM Surface."""

import argparse
import json
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": passed, "detail": detail}


def _run(command: list[str]) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)

    output = (result.stdout or result.stderr or "").strip()
    return result.returncode == 0, output


def _tcp_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


def _http_ok(url: str) -> tuple[bool, str]:
    try:
        req = Request(url, method="GET")
        with urlopen(req, timeout=5) as response:
            body = response.read(200).decode("utf-8", errors="replace")
            return 200 <= response.status < 500, f"{response.status}: {body}"
    except URLError as exc:
        return False, str(exc)
    except OSError as exc:
        return False, str(exc)


def preflight(
    ingest_dir: Path,
    bitnet_base: str,
    ollama_base: str,
    privategpt_base: str,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    if sys.version_info[:2] == (3, 11):
        checks.append(
            _check(
                "python_3_11",
                True,
                f"{sys.executable} {sys.version.split()[0]}",
            )
        )
    else:
        ok, detail = _run(["py", "-3.11", "-c", "import sys; print(sys.version)"])
        checks.append(_check("python_3_11", ok, detail))

    poetry_ok, poetry_detail = _run(["poetry", "--version"])
    uv_ok, uv_detail = _run(["uv", "--version"])
    checks.append(
        _check(
            "dependency_manager",
            poetry_ok or uv_ok,
            f"poetry={poetry_detail or 'missing'}; uv={uv_detail or 'missing'}",
        )
    )

    ollama_models = ollama_base.rstrip("/") + "/api/tags"
    ok, detail = _http_ok(ollama_models)
    checks.append(_check("ollama_models", ok, f"{ollama_models} -> {detail}"))

    pg_health = privategpt_base.rstrip("/") + "/health"
    ok, detail = _http_ok(pg_health)
    checks.append(_check("privategpt_health", ok, f"{pg_health} -> {detail}"))

    checks.append(
        _check(
            "port_11434_open",
            _tcp_open("127.0.0.1", 11434),
            "Ollama Gemma substitute",
        )
    )
    checks.append(_check("port_8000_open", _tcp_open("127.0.0.1", 8000), "PrivateGPT server"))

    if ingest_dir.exists():
        files = [
            path
            for path in ingest_dir.rglob("*")
            if path.is_file()
            and not path.name.casefold().endswith((".env", ".env.txt"))
        ]
        checks.append(
            _check(
                "ingest_dir",
                len(files) > 0,
                f"{ingest_dir} exists with {len(files)} non-env files",
            )
        )
    else:
        checks.append(_check("ingest_dir", False, f"{ingest_dir} does not exist"))

    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "scope": "D7 Wash Empire car wash land sniper only",
        "active_llm_backend": "ollama_gemma_substitute",
        "bitnet_base": bitnet_base,
        "ollama_base": ollama_base,
        "privategpt_base": privategpt_base,
        "ingest_dir": str(ingest_dir),
        "checks": checks,
    }
    report["passed"] = all(check["passed"] for check in checks)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ingest-dir", type=Path, default=Path("C:/wash-empire/privategpt-ingest"))
    parser.add_argument("--bitnet-base", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--ollama-base", default="http://127.0.0.1:11434")
    parser.add_argument("--privategpt-base", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--report-out",
        type=Path,
        default=Path("d7/reports/d7_surface_preflight_report.json"),
    )
    args = parser.parse_args()

    report = preflight(
        args.ingest_dir,
        args.bitnet_base,
        args.ollama_base,
        args.privategpt_base,
    )
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
