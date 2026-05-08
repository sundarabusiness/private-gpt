# D7 PrivateGPT Grounding Runbook

Scope: D7 Wash Empire car wash land sniper only. This fork is not for other Dynasty projects.

## Target

- Repo: `https://github.com/sundarabusiness/private-gpt`
- Upstream: `https://github.com/zylon-ai/private-gpt`
- Branch: `codex/d7-privategpt-verifier-overnight-v2-2026-05-08`
- Endpoint: `http://localhost:8000/v1/chat/completions`
- Collection: `govt-api-grounding`
- Ingest folder: `C:\wash-empire\privategpt-ingest`

## BitNet Backend

PrivateGPT is configured in `settings-d7-bitnet.yaml` to call a local OpenAI-compatible BitNet server at:

`http://127.0.0.1:8080/v1`

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

The expected BitNet server shape is OpenAI-compatible. PrivateGPT then exposes the D7 RAG endpoint on port 8000.

## PrivateGPT Setup

Use a Python runtime compatible with upstream PrivateGPT (`>=3.11,<3.12`). `uv` is the fastest proven setup path on this PC; Poetry remains compatible with upstream docs.

Fast `uv` path:

```powershell
cd C:\tmp\private-gpt
uv python install 3.11
uv venv --python 3.11 .venv
uv pip install -e ".[llms-openai-like,embeddings-huggingface,vector-stores-qdrant]" pytest
```

Run the preflight first:

```powershell
cd C:\tmp\private-gpt
.venv\Scripts\python.exe scripts\d7_surface_preflight.py
```

The report is written to:

`d7\reports\d7_surface_preflight_report.json`

Poetry path:

```powershell
cd C:\tmp\private-gpt
poetry install --extras "llms-openai-like embeddings-huggingface vector-stores-qdrant"
$env:PGPT_PROFILES="d7-bitnet"
$env:PORT="8000"
poetry run python -m private_gpt
```

`uv` start path:

```powershell
cd C:\tmp\private-gpt
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
cd C:\tmp\private-gpt
poetry run python scripts\d7_ingest_govt_api_grounding.py --base-url http://127.0.0.1:8000 --ingest-dir C:\wash-empire\privategpt-ingest
```

The manifest is written to:

`local_data/d7_privategpt/govt-api-grounding-manifest.json`

## Offline Contract Check

Before the live substrate is available, the repo contract can still be checked:

```powershell
cd C:\tmp\private-gpt
py -3.12 scripts\d7_verify_contract.py
```

The report is written to:

`d7\reports\d7_privategpt_contract_report.json`

## MCP Node

Copy `d7/mcp/privategpt_retriever_node.json` into the MCP graph. It is the exact Bobby-approved node.

## Smoke Test

```powershell
cd C:\tmp\private-gpt
poetry run python scripts\d7_privategpt_smoke.py --base-url http://127.0.0.1:8000
```

Expected behavior:

- Endpoint responds at `http://localhost:8000/v1/chat/completions`.
- Response cites only ingested source excerpts.
- If the source is missing, the response says the answer is not in context or returns empty evidence.
