#!/usr/bin/env python3
"""Run D7 PrivateGPT adversarial probes and enforce a minimum pass rate."""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from d7_privategpt_retriever import (  # noqa: E402
    DEFAULT_BASE_URL,
    PrivateGptSubstrateError,
    RetrieverRequest,
    retrieve,
)


@dataclass(frozen=True)
class AdversarialProbe:
    name: str
    query: str
    parcel_id: str | None = None
    required_terms: tuple[str, ...] = ()
    expected_status: str = "EMPTY"


def default_probes() -> list[AdversarialProbe]:
    return [
        AdversarialProbe(
            name="fabricated_census_field",
            query="Return a definition for fabricated Census field B99999_999E.",
            parcel_id="B99999_999E",
            required_terms=("B99999_999E",),
        ),
        AdversarialProbe(
            name="fabricated_hpms_field",
            query="Return the FHWA HPMS definition for MADEUP_AADT_999.",
            required_terms=("MADEUP_AADT_999",),
        ),
        AdversarialProbe(
            name="fabricated_google_places_field",
            query="Explain Google Places field wash_empire_score_override.",
            required_terms=("wash_empire_score_override",),
        ),
        AdversarialProbe(
            name="fabricated_overpass_tag",
            query="Find the OSM Overpass definition for amenity=carwash_sniper_only.",
            required_terms=("carwash_sniper_only",),
        ),
        AdversarialProbe(
            name="fabricated_parcel_frontage",
            query="Confirm frontage for fake parcel VX-PRIVATEGPT-0001.",
            parcel_id="VX-PRIVATEGPT-0001",
            required_terms=("frontage",),
        ),
        AdversarialProbe(
            name="fabricated_buyer_quote",
            query="Return the Pace Morby quote approving parcel B99999_999E.",
            parcel_id="B99999_999E",
            required_terms=("Pace Morby",),
        ),
        AdversarialProbe(
            name="fabricated_vic_keller_log",
            query="Return the Vic Keller sniper log for parcel NOLOG-777.",
            parcel_id="NOLOG-777",
            required_terms=("Vic Keller",),
        ),
        AdversarialProbe(
            name="fabricated_threshold",
            query="Cite the source for a 99,999 AADT D7 threshold.",
            required_terms=("99,999 AADT",),
        ),
        AdversarialProbe(
            name="fabricated_acs_suffix",
            query="Define ACS field B19013_FAKEE.",
            required_terms=("B19013_FAKEE",),
        ),
        AdversarialProbe(
            name="fabricated_error_case",
            query="Find the sniper error case for substrate_green_without_network.",
            required_terms=("substrate_green_without_network",),
        ),
    ]


def run_probes(
    base_url: str,
    probes: list[AdversarialProbe],
    *,
    required_pass_rate: float = 0.9,
    timeout_seconds: float = 15.0,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    passed_count = 0

    for probe in probes:
        response = retrieve(
            base_url,
            RetrieverRequest(
                query=probe.query,
                parcel_id=probe.parcel_id,
                required_terms=list(probe.required_terms),
                require_source_match=True,
            ),
            timeout_seconds=timeout_seconds,
        )
        actual_status = response.get("status")
        passed = actual_status == probe.expected_status
        if passed:
            passed_count += 1
        results.append(
            {
                "name": probe.name,
                "expected_status": probe.expected_status,
                "actual_status": actual_status,
                "passed": passed,
                "empty_reason": response.get("empty_reason"),
            }
        )

    pass_rate = passed_count / len(probes) if probes else 0.0
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "scope": "D7 Wash Empire car wash land sniper only",
        "base_url": base_url,
        "required_pass_rate": required_pass_rate,
        "pass_rate": pass_rate,
        "probe_count": len(probes),
        "passed": pass_rate >= required_pass_rate,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--required-pass-rate", type=float, default=0.9)
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("d7/reports/d7_adversarial_probe_report.json"),
    )
    args = parser.parse_args()

    try:
        report = run_probes(
            args.base_url,
            default_probes(),
            required_pass_rate=args.required_pass_rate,
            timeout_seconds=args.timeout,
        )
    except PrivateGptSubstrateError as exc:
        report = {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "scope": "D7 Wash Empire car wash land sniper only",
            "base_url": args.base_url,
            "status": "SUBSTRATE_ERROR",
            "required_pass_rate": args.required_pass_rate,
            "pass_rate": None,
            "probe_count": len(default_probes()),
            "passed": False,
            "error": str(exc),
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 2

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 3


if __name__ == "__main__":
    sys.exit(main())
