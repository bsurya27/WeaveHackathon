# Startup Advisor — multi-agent pipeline skeleton

Plain async Python pipeline for pitch-deck review: specialist fan-out, two-stage decider fan-out/fan-in, synthesis. Agent bodies are stubbed; Weave tracing and asyncio structure are real.

## Prerequisites

- Python 3.11+
- Weights & Biases account (`wandb login` — no Anthropic API key needed for this pass)

## Setup

```powershell
# from repo root
python -m venv weavehack
.\weavehack\Scripts\Activate.ps1
pip install -r requirements.txt
wandb login
```

## Streamlit UI (intake + panel + follow-up)

```powershell
.\weavehack\Scripts\Activate.ps1
pip install streamlit
streamlit run streamlit_app.py
```

Opens at http://localhost:8501 — conversational intake, run panel, then follow-up Q&A.

## CLI pipeline (dummy deck)

```powershell
.\weavehack\Scripts\Activate.ps1
python main.py
```

Expected output:

1. JSON `FinalBrief` printed to stdout
2. `session: <id> — saved` with a file at `sessions/<id>.json`
3. A nested Weave trace in your W&B project (`startup-advisor` by default — change in `config.py`)

## Pipeline

```
intake
  → 4 specialists (parallel)
  → 3 deciders stage 1 (parallel)
  → 3 deciders stage 2 (parallel, each sees peers' stage-1)
  → synthesis
```

## Files

| File | Role |
|------|------|
| `schemas.py` | Pydantic models (thin, provisional) |
| `config.py` | Model names + Weave project |
| `llm.py` | Async Anthropic structured-output wrapper (`@weave.op`) |
| `agents.py` | Stub agent ops — swap `# TODO` line for `llm.structured(...)` |
| `orchestrator.py` | `run()` with `asyncio.gather` fan-out stages |
| `session.py` | Persist full run to `sessions/` |
| `fixtures.py` | `DUMMY_PITCH_DECK` test input |
| `main.py` | Entry point |

## Next steps

Replace stub bodies in `agents.py` with real prompts + `llm.structured()` calls. Set `ANTHROPIC_API_KEY` when enabling LLM calls.
