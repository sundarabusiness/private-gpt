#!/usr/bin/env python3
"""Fail-closed client for the D7 PrivateGPT retriever endpoint."""

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any

import requests


class PrivateGptSubstrateError(RuntimeError):
    """Raised when PrivateGPT cannot be trusted as an available substrate."""


@dataclass(frozen=True)
class RetrieverRequest:
    query: str
    parcel_id: str | None = None
    required_terms: list[str] | None = None
    limit: int = 10
    min_score: float | None = None
    require_source_match: bool = True

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "query": self.query,
            "parcel_id": self.parcel_id,
            "required_terms": self.required_terms or [],
            "limit": self.limit,
            "require_source_match": self.require_source_match,
        }
        if self.min_score is not None:
            payload["min_score"] = self.min_score
        return payload


def retrieve(
    base_url: str,
    request: RetrieverRequest,
    timeout_seconds: float = 15.0,
) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/v1/d7/privategpt_retriever"
    try:
        response = requests.post(url, json=request.to_payload(), timeout=timeout_seconds)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise PrivateGptSubstrateError(
            f"PrivateGPT substrate unavailable at {url}: {exc}"
        ) from exc

    data = response.json()
    if not isinstance(data, dict):
        raise PrivateGptSubstrateError("PrivateGPT returned a non-object JSON payload")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--query", required=True)
    parser.add_argument("--parcel-id")
    parser.add_argument("--required-term", action="append", default=[])
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--min-score", type=float)
    parser.add_argument("--allow-unmatched-source", action="store_true")
    parser.add_argument("--expect-empty", action="store_true")
    args = parser.parse_args()

    req = RetrieverRequest(
        query=args.query,
        parcel_id=args.parcel_id,
        required_terms=args.required_term,
        limit=args.limit,
        min_score=args.min_score,
        require_source_match=not args.allow_unmatched_source,
    )

    try:
        result = retrieve(args.base_url, req)
    except PrivateGptSubstrateError as exc:
        print(json.dumps({"status": "SUBSTRATE_ERROR", "error": str(exc)}))
        return 2

    print(json.dumps(result, indent=2))
    if args.expect_empty and result.get("status") != "EMPTY":
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

