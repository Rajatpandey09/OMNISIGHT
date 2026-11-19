# Run modes (no API key needed)

Set VISION_PROVIDER in your local .env (never commit .env).

| Mode | VISION_PROVIDER | Key? | What it is |
|---|---|---|---|
| Mock | `mock` | No | Canned "cannot determine" reply. Proves the pipeline runs. |
| Heuristic | `heuristic` | No | Reads metrics only (overflow, off-screen buttons, hidden controls). NOT a vision model; results are labelled `heuristic`. |
| Local vision model | `ollama` | No | Real screenshot analysis on your laptop. Needs enough RAM and a vision-capable model. |

Cloud providers were not implemented because no API keys were available. The provider
interface (vision/providers/base.py) lets one be added later with a single new file.

## Fallback chain
A comma list is tried left to right; the next one is used when a provider fails
(timeout, Ollama not running, model not set). Example:

    ollama,heuristic

The result's `provider` field shows which one actually answered.
(A provider that answers with invalid JSON is reported as invalid_output; it does not fall through.)

## Trying Ollama
1. Install Ollama from ollama.com and start it.
2. Browse the Ollama library for a vision-capable model. Check the model page for its
   download size and keep it well under your free RAM.
3. Download it with `ollama pull <model-name>`.
4. In your .env set VISION_PROVIDER to ollama and VISION_MODEL to that model name.
5. Run `python run_analysis.py path/to/scan_result.json --timeout 240`.
6. Score it with `python run_eval.py --provider ollama` once case data exists.
Small local models often fail at strict JSON. That is expected: validation turns it into
`invalid_output` and the scan continues. Record this in your evaluation table.

## Secrets
- Never commit a .env file or any key. `tests/test_no_secrets.py` fails if a key-like
  string is found in the repo. Member 4 can also check this when reviewing PRs.
- If a key is ever committed, revoke it at the provider immediately; deleting the file is not enough.
