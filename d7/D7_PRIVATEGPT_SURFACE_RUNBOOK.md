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
git clone https://github.com/microsoft/BitNet C:\BitNet
cd C:\BitNet
# Follow microsoft/BitNet setup for the ARM Surface.
# After build, run llama-server on 127.0.0.1:8080 with the BitNet GGUF model.
```

The expected BitNet server shape is OpenAI-compatible. PrivateGPT then exposes the D7 RAG endpoint on port 8000.

## PrivateGPT Setup

Use a Python runtime compatible with upstream PrivateGPT (`>=3.11,<3.12`) and Poetry.

```powershell
cd C:\tmp\private-gpt
poetry install --extras "llms-openai-like embeddings-huggingface vector-stores-qdrant"
$env:PGPT_PROFILES="d7-bitnet"
$env:PORT="8000"
poetry run python -m private_gpt
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

