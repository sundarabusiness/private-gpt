#!/usr/bin/env python3
"""Smoke-test D7 PrivateGPT grounding against the OpenAI-compatible chat endpoint."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

import requests


SYSTEM_PROMPT = (
    "You are a zero-hallucination grounding engine. ONLY return verbatim "
    "excerpts from the ingested official API docs, data dictionaries, and past "
    "sniper logs. Never invent explanations. Always include the exact field "
    "name and source document title."
)


def build_user_message(payload: dict[str, Any]) -> str:
    return (
        "Raw JSON payload:\n"
        + json.dumps(payload["raw_json_payload"], indent=2)
        + "\n\nSpecific question:\n"
        + payload["specific_question"]
        + "\n\nReturn ONLY grounded excerpts. Cite exact source document and field. "
        "No opinions, no summaries, no hallucinations.\n"
        f"Every number or definition must include [Source: PrivateGPT | Field: XXX | Pulled: {date.today().isoformat()}]."
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--payload",
        type=Path,
        default=Path("d7/prompts/sample_census_smoke_payload.json"),
    )
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    payload = json.loads(args.payload.read_text(encoding="utf-8"))
    request_body = {
        "model": "private-gpt",
        "temperature": 0.0,
        "max_tokens": 1024,
        "use_context": True,
        "include_sources": True,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_message(payload)},
        ],
    }

    url = args.base_url.rstrip("/") + "/v1/chat/completions"
    try:
        response = requests.post(url, json=request_body, timeout=args.timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(json.dumps({"status": "SUBSTRATE_ERROR", "endpoint": url, "error": str(exc)}))
        return 2

    print(json.dumps(response.json(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

