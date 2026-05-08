#!/usr/bin/env python3
"""Offline contract verifier for the D7 PrivateGPT grounding PR."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPECTED_NODE = {
    "agent_name": "PrivateGPT_Retriever",
    "type": "retriever",
    "backend": "privategpt_local",
    "endpoint": "http://localhost:8000/v1/chat/completions",
    "collection": "govt-api-grounding",
    "temperature": 0.0,
    "max_tokens": 1024,
    "system_prompt": (
        "You are a zero-hallucination grounding engine. ONLY return verbatim "
        "excerpts from the ingested official API docs, data dictionaries, and "
        "past sniper logs. Never invent explanations. Always include the exact "
        "field name and source document title."
    ),
    "input_schema": ["raw_json_payload", "specific_question"],
    "output_schema": ["grounded_excerpts", "citations"],
    "next_nodes": ["Main_Reasoning_Agent_5080", "Fact_Checker_BitNet"],
}

EXPECTED_PROMPT = """Raw JSON payload:
{entire raw API response here}

Specific question:
Explain what B01001_001E and B19013_001E mean for buyer appeal on this parcel. Also confirm the exact definition of AADT from the FHWA HPMS dictionary and whether the value meets the 13,000+ Pillar 3 threshold.

Return ONLY grounded excerpts. Cite exact source document and field. No opinions, no summaries, no hallucinations.
"""


def _result(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": passed, "detail": detail}


def verify(root: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    node_path = root / "d7" / "mcp" / "privategpt_retriever_node.json"
    node = json.loads(node_path.read_text(encoding="utf-8"))
    checks.append(_result("exact_mcp_node", node == EXPECTED_NODE, str(node_path)))

    prompt_path = root / "d7" / "prompts" / "privategpt_retriever_prompt_template.txt"
    prompt = prompt_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    checks.append(_result("exact_prompt_template", prompt == EXPECTED_PROMPT, str(prompt_path)))

    settings_path = root / "settings-d7-bitnet.yaml"
    settings = settings_path.read_text(encoding="utf-8")
    checks.append(_result("privategpt_port_8000", "port: ${PORT:8000}" in settings, str(settings_path)))
    checks.append(_result("collection_name", "collection_name: govt-api-grounding" in settings, str(settings_path)))
    checks.append(_result("bitnet_openai_base", "BITNET_OPENAI_BASE:http://127.0.0.1:8080/v1" in settings, str(settings_path)))

    vector_store_path = root / "private_gpt" / "components" / "vector_store" / "vector_store_component.py"
    vector_store = vector_store_path.read_text(encoding="utf-8")
    checks.append(_result("qdrant_collection_parameterized", "settings.qdrant.collection_name" in vector_store, str(vector_store_path)))

    route_path = root / "private_gpt" / "server" / "d7_retriever" / "d7_retriever_router.py"
    route = route_path.read_text(encoding="utf-8")
    checks.append(_result("fabricated_id_empty_guard", "status: Literal[\"FOUND\", \"EMPTY\"]" in route and "no_source_match" in route, str(route_path)))

    manifest_path = root / "d7" / "grounding_sources_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks.append(
        _result(
            "grounding_source_groups",
            manifest.get("collection") == "govt-api-grounding"
            and len(manifest.get("required_source_groups", [])) == 6,
            str(manifest_path),
        )
    )

    report = {
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "scope": "D7 Wash Empire car wash land sniper only",
        "endpoint": EXPECTED_NODE["endpoint"],
        "collection": EXPECTED_NODE["collection"],
        "checks": checks,
    }
    report["passed"] = all(check["passed"] for check in checks)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--report-out",
        type=Path,
        default=Path("d7/reports/d7_privategpt_contract_report.json"),
    )
    args = parser.parse_args()

    report = verify(args.root)
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())

