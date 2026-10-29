# OMNISIGHT

## Vision module (Member 3)

Interprets scan screenshots and page metrics and returns structured, validated findings.
It never executes anything the model writes, and a failure in it never crashes a scan.

### Setup
```
pip install -r requirements.txt
cp .env.example .env     # .env is git-ignored; never commit it
python -m pytest         # all tests should pass
```

### Run modes (no API key needed)
Set `VISION_PROVIDER` in `.env`:

| Value | What it does |
|---|---|
| `mock` | Canned "cannot determine" reply. Proves the pipeline runs. |
| `heuristic` | Reads metrics only (overflow, off-screen buttons, hidden controls). Not a vision model; results are labelled `heuristic`. |
| `ollama` | Analyses real screenshots with a local vision model. Set `VISION_MODEL` to the model name. |
| `ollama,heuristic` | Fallback chain: tries Ollama, falls back to the heuristic if it fails. |

See `docs/run_modes.md` for the Ollama setup steps.

### Usage
```
python run_analysis.py path/to/scan_result.json --provider heuristic
python run_analysis.py path/to/scan_result.json --provider ollama --timeout 240
python run_eval.py --provider heuristic
```
Input: a `scan_result.json` with `scan_id` and a `results` list (viewport, width, height,
screenshot filename, metrics). The screenshots must be in the same folder as the JSON.
Output: `analysis.json` with one entry per viewport.

### Outcomes
Each viewport result has an outcome: `ok`, `no_credentials`, `provider_error`,
`invalid_output` or `input_error`. Findings carry an issue type, element, severity, evidence,
confidence and a `detected` or `inconclusive` status. Uncertainty is never reported as a pass.

### Limitations
- The vision model sees the screenshot and metrics, not the page CSS, so any suggested
  cause is a hypothesis, not a verified diagnosis.
- Small local models often return invalid JSON; this is recorded as `invalid_output`.
- Cloud providers are not implemented. The interface in `vision/providers/base.py`
  allows adding one with a single new file.
- Patch (diff) suggestions are not built yet.


# OmniSight Backend & Browser Automation

Backend service built with **FastAPI**, **Uvicorn**, and **Playwright** for headless browser navigation, responsive screenshot capture, and layout metric extraction.

## Setup Instructions

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt

