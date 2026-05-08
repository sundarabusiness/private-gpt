# D7 PrivateGPT Grounding Runbook

Scope: D7 Wash Empire car wash land sniper only. This fork is not for other Dynasty projects.

## Target

- Repo: `https://github.com/sundarabusiness/private-gpt`
- Upstream: `https://github.com/zylon-ai/private-gpt`
- Branch: `codex/d7-privategpt-verifier-overnight-v2-2026-05-08`
- Endpoint: `http://localhost:8000/v1/chat/completions`
- Collection: `govt-api-grounding`
- Ingest folder: `C:\wash-empire\privategpt-ingest`

## Ollama Gemma Substitute

Path B is active on retrobob while the full Microsoft BitNet deploy is pending.
This follows the v2 plan Phase 9 risk table: BitNet unavailable -> local Ollama
small-model substitute.

PrivateGPT is configured in `settings-d7-bitnet.yaml` to call local Ollama:

- Ollama base: `http://127.0.0.1:11434`
- OpenAI-compatible base: `http://127.0.0.1:11434/v1`
- LLM model: `gemma3:4b` (loaded locally; chosen because `gemma2:9b` and `gemma:4b-it` were not loaded)
- Embedding model: `nomic-embed-text:latest`

The D7 PrivateGPT API still exposes:

`http://localhost:8000/v1/chat/completions`

## Future BitNet Backend

On ARM Surfaces, build/run Microsoft's BitNet server so it exposes `/v1/chat/completions`:

```powershell
# Run from a VS2022 Developer PowerShell with CMake + Clang available.
git clone --recursive https://github.com/microsoft/BitNet C:\BitNet
cd C:\BitNet
conda create -n bitnet-cpp python=3.9
conda activate bitnet-cpp
pip install -r requirements.txt
huggingface-cli download microsoft/BitNet-b1.58-2B-4T-gguf --local-dir models/BitNet-b1.58-2B-4T
python setup_env.py -md models/BitNet-b1.58-2B-4T -q i2_s
python run_inference_server.py -m models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf --host 127.0.0.1 --port 8080 -c 4096 -n 1024 --temperature 0.0
```

The expected BitNet server shape is OpenAI-compatible. When BitNet is deployed,
switch the active profile back to the BitNet base on `127.0.0.1:8080/v1`.

## PrivateGPT Setup

Use a Python runtime compatible with upstream PrivateGPT (`>=3.11,<3.12`). `uv` is the fastest proven setup path on this PC; Poetry remains compatible with upstream docs.

Fast `uv` path:

```powershell
cd C:\private-gpt-d7
uv python install 3.11
uv venv --python 3.11 .venv
uv pip install -e ".[llms-ollama,embeddings-ollama,vector-stores-qdrant]" pytest
```

Run the preflight first:

```powershell
cd C:\private-gpt-d7
.venv\Scripts\python.exe scripts\d7_surface_preflight.py
```

The report is written to:

`d7\reports\d7_surface_preflight_report.json`

Poetry path:

```powershell
cd C:\private-gpt-d7
poetry install --extras "llms-ollama embeddings-ollama vector-stores-qdrant"
$env:PGPT_PROFILES="d7-bitnet"
$env:PORT="8000"
poetry run python -m private_gpt
```

`uv` start path:

```powershell
cd C:\private-gpt-d7
$env:PGPT_PROFILES="d7-bitnet"
$env:PORT="8000"
.venv\Scripts\python.exe -m private_gpt
```

## Ingest

The folder must contain only D7 grounding material:

- Official Census API docs and ACS data dictionary PDFs
- FHWA HPMS data dictionary
- All 16 government/API docs used by the sniper
- Sample raw JSON responses from prior sniper runs
- All sniper run logs and error cases

Run:

```powershell
cd C:\private-gpt-d7
.venv\Scripts\python.exe scripts\d7_ingest_govt_api_grounding.py --base-url http://127.0.0.1:8000 --ingest-dir C:\wash-empire\privategpt-ingest
```

The manifest is written to:

`local_data/d7_privategpt/govt-api-grounding-manifest.json`

## Offline Contract Check

Before the live substrate is available, the repo contract can still be checked:

```powershell
cd C:\private-gpt-d7
.venv\Scripts\python.exe scripts\d7_verify_contract.py
```

The report is written to:

`d7\reports\d7_privategpt_contract_report.json`

## Adversarial Probe Gate

Run the adversarial probe after PrivateGPT is live and ingestion is complete:

```powershell
cd C:\private-gpt-d7
.venv\Scripts\python.exe scripts\d7_adversarial_probe.py --base-url http://127.0.0.1:8000 --required-pass-rate 0.9
```

This gate sends 10 fabricated D7/Census/FHWA/API/log probes and requires at least a 90% EMPTY rate. If PrivateGPT is unreachable, it writes `SUBSTRATE_ERROR` and exits non-zero.

## MCP Node

Copy `d7/mcp/privategpt_retriever_node.json` into the MCP graph. It is the exact Bobby-approved node.

## Smoke Test

```powershell
cd C:\private-gpt-d7
.venv\Scripts\python.exe scripts\d7_privategpt_smoke.py --base-url http://127.0.0.1:8000
```

Expected behavior:

- Endpoint responds at `http://localhost:8000/v1/chat/completions`.
- Bobby's zero-hallucination prompt returns deterministic JSON with `grounded_excerpts` and `citations`.
- If the source is missing, evidence arrays are empty instead of generated prose.
