# Vision model provider comparison (Week 1)

Owner: Member 3. Status: DRAFT. Every cell marked VERIFY must be checked on the
provider's official pricing/docs page and dated before we rely on it.
Do not call any provider "free" until the current limits are confirmed.

Date checked: ____ (fill in)

## Criteria
Access, cost, latency, image support, data handling, laptop limits (from the work guide).

| Criterion | Gemini API (Google) | OpenAI API | Anthropic API | Local VLM via Ollama |
|---|---|---|---|---|
| Access (account, key, region) | VERIFY | VERIFY | VERIFY | No key; install Ollama and pull a vision model |
| Cost / free tier / rate limits | VERIFY | VERIFY | VERIFY | No per-call cost; uses own hardware |
| Image input supported | Yes (VERIFY model) | Yes (VERIFY model) | Yes (VERIFY model) | Depends on model; pick a vision-capable one |
| JSON / structured output | VERIFY | VERIFY | VERIFY | Weaker; needs strict validation and retries |
| Latency per screenshot | MEASURE | MEASURE | MEASURE | MEASURE (laptop dependent) |
| Data handling (are screenshots stored/trained on?) | VERIFY | VERIFY | VERIFY | Stays on the laptop |
| Laptop limits | None (cloud) | None (cloud) | None (cloud) | RAM/VRAM and speed limits; MEASURE |
| Works offline / no key | No | No | No | Yes |

## How to measure latency and quality
Run the same 3 labelled cases (see eval/labelled_cases.json) on each candidate:
one overflow, one off-screen button, one clean page. Record seconds per call,
whether the output was valid JSON, and whether the finding was correct.

| Provider/model | Case | Seconds | Valid JSON? | Correct? | Notes |
|---|---|---|---|---|---|
| | | | | | |

## Decision (fill after testing)
Primary provider: ____   Fallback: mock provider (offline) / ____
Reason: ____
Test-set screenshots contain only our own demo site, so data-handling risk is low,
but we still never send secrets, cookies or unrelated source code.
