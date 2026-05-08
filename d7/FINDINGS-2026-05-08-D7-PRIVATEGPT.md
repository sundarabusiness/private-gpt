# D7 PrivateGPT Grounding Findings - 2026-05-08

## Verdict

GREEN for Path B deployment on retrobob.

PrivateGPT is live at `http://localhost:8000`, the `govt-api-grounding` collection is loaded, and the adversarial probe gate passed at `1.00`.

## Completed

- Forked the exact Zylon repo: `zylon-ai/private-gpt` -> `sundarabusiness/private-gpt`.
- Created branch: `codex/d7-privategpt-verifier-overnight-v2-2026-05-08`.
- Added D7-only settings profile: `settings-d7-bitnet.yaml`.
- Swapped the live runtime to Ollama Gemma (`gemma3:4b`) as the BitNet substitute while full Microsoft BitNet is pending, per the v2 plan Phase 9 risk table.
- Set PrivateGPT server target to `http://localhost:8000`.
- Added Qdrant collection-name support and configured exact collection: `govt-api-grounding`.
- Added Bobby's exact MCP graph node JSON at `d7/mcp/privategpt_retriever_node.json`.
- Added exact retriever prompt template at `d7/prompts/privategpt_retriever_prompt_template.txt`.
- Added sample Census smoke payload at `d7/prompts/sample_census_smoke_payload.json`.
- Added ingestion runner for `C:\wash-empire\privategpt-ingest`.
- Added smoke runner for `http://localhost:8000/v1/chat/completions`.
- Added a D7-specific source-match retriever route and tests to fail empty on unsupported parcel IDs.
- Added a D7 grounding guard on `/v1/chat/completions`; Bobby's zero-hallucination prompt now bypasses freeform generation and returns deterministic `grounded_excerpts` plus `citations`.
- Added exact-term fallback retrieval for field tokens such as `B01001_001E`, `B19013_001E`, and `AADT`, with official/source-index ranking ahead of generic semantic hits.
- Added offline contract verifier for exact MCP node, prompt, endpoint, collection, and source manifest.
- Added offline contract report at `d7/reports/d7_privategpt_contract_report.json`.
- Added ARM Surface preflight checker for Python 3.11, dependency manager, BitNet, PrivateGPT, ports, and ingest folder.
- Added adversarial probe runner for 10 fabricated D7/Census/FHWA/API/log probes with a 90% pass-rate gate.

## Live Deployment

Confirmed on retrobob:

- PrivateGPT health: `http://127.0.0.1:8000/health -> {"status":"ok"}`.
- Active backend: Ollama Gemma substitute at `http://127.0.0.1:11434`.
- Active model: `gemma3:4b`.
- Active embedding model: `nomic-embed-text:latest`.
- Ingest folder: `C:\wash-empire\privategpt-ingest`.
- Loaded collection: `govt-api-grounding`.
- Loaded files/chunks: `23` unique ingest files, `133` indexed chunks.
- Full Microsoft BitNet remains pending; this is the documented v2 Phase 9 substitute.

## Verification Run

- Surface preflight passed with Ollama Gemma substitute: `d7/reports/d7_surface_preflight_report.json`.
- Offline contract verifier passed: `d7/reports/d7_privategpt_contract_report.json`.
- Focused pytest passed: `12 passed`.
- `git diff --check` passed with no whitespace errors.
- Ingest runner loaded all 23 prepared files and wrote `local_data\d7_privategpt\govt-api-grounding-manifest.json`.
- OpenAI-compatible chat smoke returned deterministic JSON with `grounded_excerpts` and `citations`.
- Positive source checks returned exact evidence for `B01001_001E`, `B19013_001E`, and FHWA `AADT`.
- Adversarial probe gate passed: `10/10`, pass rate `1.00`, report at `d7/reports/d7_adversarial_probe_report.json`.

## Handoff Notes

1. Review the Ollama Gemma swap as the temporary BitNet substitute.
2. Review the deterministic D7 chat grounding guard on `/v1/chat/completions`.
3. Review `d7/reports/d7_adversarial_probe_report.json` before merge.
4. When Microsoft BitNet is fully deployed, switch `settings-d7-bitnet.yaml` back to the BitNet OpenAI-compatible base and rerun all gates.

## Expected Final Endpoint

`http://localhost:8000/v1/chat/completions`

## Expected Collection

`govt-api-grounding`

## MCP Node

See `d7/mcp/privategpt_retriever_node.json`.
