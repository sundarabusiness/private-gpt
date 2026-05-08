# D7 PrivateGPT Grounding Findings - 2026-05-08

## Verdict

Fork and branch are prepared for D7 Wash Empire car wash land sniper grounding, but the endpoint is not live on this PC yet.

## Completed

- Forked the exact Zylon repo: `zylon-ai/private-gpt` -> `sundarabusiness/private-gpt`.
- Created branch: `codex/d7-privategpt-verifier-overnight-v2-2026-05-08`.
- Added D7-only settings profile: `settings-d7-bitnet.yaml`.
- Set PrivateGPT server target to `http://localhost:8000`.
- Added Qdrant collection-name support and configured exact collection: `govt-api-grounding`.
- Added Bobby's exact MCP graph node JSON at `d7/mcp/privategpt_retriever_node.json`.
- Added exact retriever prompt template at `d7/prompts/privategpt_retriever_prompt_template.txt`.
- Added sample Census smoke payload at `d7/prompts/sample_census_smoke_payload.json`.
- Added ingestion runner for `C:\wash-empire\privategpt-ingest`.
- Added smoke runner for `http://localhost:8000/v1/chat/completions`.
- Added a D7-specific source-match retriever route and tests to fail empty on unsupported parcel IDs.
- Added offline contract verifier for exact MCP node, prompt, endpoint, collection, and source manifest.
- Added offline contract report at `d7/reports/d7_privategpt_contract_report.json`.
- Added ARM Surface preflight checker for Python 3.11, Poetry, BitNet, PrivateGPT, ports, and ingest folder.

## Not Live Yet

This machine cannot honestly confirm live service or loaded collection yet:

- `C:\wash-empire\privategpt-ingest` was not present.
- No Python 3.11 runtime was installed; upstream PrivateGPT requires `>=3.11,<3.12`.
- Poetry was not installed.
- No local Microsoft BitNet checkout/server was present.
- No listener was active on ports `8000`, `8001`, or `8080`; only Ollama was listening on `11434`.

## Verification Run

- Python compile check passed for all changed Python files.
- `git diff --check` passed with no whitespace errors.
- Offline contract verifier passed: exact MCP node, prompt, port, collection, BitNet base, Qdrant collection wiring, fabricated-id EMPTY guard, and source manifest.
- Script-only pytest passed: `2 passed`.
- D7 ingest runner returned `MISSING_INGEST_DIR` for `C:\wash-empire\privategpt-ingest`.
- D7 sample Census smoke returned `SUBSTRATE_ERROR` because `http://127.0.0.1:8000/v1/chat/completions` is not listening.
- Surface preflight report documents the same live-runtime blockers at `d7/reports/d7_surface_preflight_report.json`.
- Focused pytest could not start because upstream PrivateGPT dependencies are not installed locally: `ModuleNotFoundError: No module named 'injector'`.

## Required Morning Actions

1. Put the prepared D7 grounding files in `C:\wash-empire\privategpt-ingest`.
2. Install Python 3.11 and Poetry on the ARM Surface.
3. Build/run Microsoft BitNet so its OpenAI-compatible server listens at `http://127.0.0.1:8080/v1`.
4. Start PrivateGPT with `settings-d7-bitnet.yaml` and `PORT=8000`.
5. Run `scripts\d7_ingest_govt_api_grounding.py`.
6. Run `scripts\d7_privategpt_smoke.py`.

## Expected Final Endpoint

`http://localhost:8000/v1/chat/completions`

## Expected Collection

`govt-api-grounding`

## MCP Node

See `d7/mcp/privategpt_retriever_node.json`.
