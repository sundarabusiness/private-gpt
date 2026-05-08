#!/usr/bin/env python3
"""Ingest D7 sniper grounding files into PrivateGPT's govt-api-grounding collection."""

import argparse
import json
import mimetypes
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


DEFAULT_INGEST_DIR = Path("C:/wash-empire/privategpt-ingest")
SUPPORTED_SUFFIXES = {
    ".csv",
    ".html",
    ".json",
    ".jsonl",
    ".log",
    ".md",
    ".pdf",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}


def iter_ingest_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix.casefold() in SUPPORTED_SUFFIXES
        and not path.name.casefold().endswith((".env", ".env.txt"))
    )


def ingest_file(base_url: str, path: Path, timeout: float) -> dict[str, Any]:
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    with path.open("rb") as handle:
        response = requests.post(
            base_url.rstrip("/") + "/v1/ingest/file",
            files={"file": (path.name, handle, content_type)},
            timeout=timeout,
        )
    response.raise_for_status()
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--ingest-dir", type=Path, default=DEFAULT_INGEST_DIR)
    parser.add_argument(
        "--manifest-out",
        type=Path,
        default=Path("local_data/d7_privategpt/govt-api-grounding-manifest.json"),
    )
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    if not args.ingest_dir.exists():
        print(
            json.dumps(
                {
                    "status": "MISSING_INGEST_DIR",
                    "path": str(args.ingest_dir),
                    "message": "Prepared D7 grounding folder was not found.",
                },
                indent=2,
            )
        )
        return 2

    files = iter_ingest_files(args.ingest_dir)
    if not files:
        print(
            json.dumps(
                {
                    "status": "EMPTY_INGEST_DIR",
                    "path": str(args.ingest_dir),
                    "message": "No supported grounding files found.",
                },
                indent=2,
            )
        )
        return 2

    manifest: dict[str, Any] = {
        "collection": "govt-api-grounding",
        "base_url": args.base_url,
        "ingest_dir": str(args.ingest_dir),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "files": [],
    }

    for path in files:
        result = ingest_file(args.base_url, path, args.timeout)
        manifest["files"].append(
            {
                "path": str(path),
                "bytes": path.stat().st_size,
                "response": result,
            }
        )
        print(f"INGESTED {path}")

    args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"status": "LOADED", "manifest": str(args.manifest_out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

