# Original Infotact OmniSight requirements — traceability

Source of truth: *Infotact Solutions Project Document — Advanced Generative AI Engineering (Vol. II)*, Project 1, pages 1–2. The four-member execution guide is used for ownership and prototype acceptance; it does not erase the original brief's Week 3 GitHub integration and Week 4 optimisation work.

Status vocabulary: **Implemented in code** means source exists; **Integrated, needs runtime proof** means the live workflow is wired but must be executed on the team's machine; **Not complete** means no evidence of implementation in this branch.

| Original requirement | Current evidence in repository | Status / remaining proof |
|---|---|---|
| Playwright navigation, checkout-flow interactions, responsive screenshots | `main.py` Playwright worker; desktop/mobile viewport screenshots and metrics | Partially implemented. Browser navigation/capture exists; the complete mock e-commerce checkout interaction flow still needs a recorded demo. |
| FastAPI webhook receiver for simulated CI/CD events | FastAPI app and scan API in `main.py` | Not complete. A dedicated CI/CD webhook receiver and simulated build event are not demonstrated. |
| VLM receives screenshots and raw HTML together | `main.py` now stores bounded body HTML with each viewport capture; `vision/pipeline.py`; `vision_api.py` | Integrated in code. Run `POST /api/ai/analyze/{scan_id}` and retain returned JSON as runtime evidence. |
| Screenshot-only hidden-submit audit | `vision_api.py` supports `?screenshot_only=true`; vision prompt/schema | Endpoint implemented. Run against the hidden-control fixture and record whether the VLM can or cannot see it; screenshot-only cannot reliably infer invisible DOM state. |
| Parse AI response and extract CSS/React code fix | `vision/patches.py` validates structured CSS proposals | CSS proposal path exists. React source-code patch extraction is not demonstrated. |
| Plan → Execute → Evaluate with retry | `vision/heal.py` | Integrated through `POST /api/ai/heal/{scan_id}`; runtime proof still required. It retries up to the request limit and tests only in a disposable browser context. |
| Apply CSS to local DOM and capture a new screenshot | `vision_api.py` uses isolated Playwright context and returns the self-healing result | Implemented as an isolated browser test. It does not edit the original website or repository files. |
| VLM compares before/after and evaluates the fix | `vision/patches.py` `verify_fix` + `combine_verdicts`; called by `vision/heal.py` | Integrated in code. Runtime proof required with real Ollama vision model and a known defect. |
| GitHub branch, commit and pull request | No automated PR creation route/workflow found | Not complete. Do not claim automated PR delivery. Human-reviewed Git workflow remains manual. |
| Image chunking/cropping to reduce tokens and latency | Existing `vision/imaging.py`, crop/chunk utilities and evaluation scripts | Code exists; measure on real captured pages and include timings/token or image-size comparison. |
| QA dashboard to approve/reject fixes | `index.html`, `script.js`, `api.js`; Q&A widget is separate | Dashboard and review UI exist. VLM analysis and isolated healing controls are now wired. Verify at 1366px and 390px. |
| Technical report and visual evidence | README, test fixtures, evaluation utilities | Evidence pack still needs actual run IDs, before/after screenshots, results, false positives/negatives and member contributions. |

## End-to-end local run

1. Start Ollama and ensure the vision-capable model is available:
   `ollama pull qwen2.5vl:3b`
2. Copy `.env.example` to `.env`; set `VISION_PROVIDER=ollama`, `VISION_MODEL=qwen2.5vl:3b`, `VISION_QA_MODEL=qwen2.5vl:3b`.
3. Start the frontend on port 5500 and API on port 8000. Install Chromium with `playwright install chromium`.
4. Run a scan against an allow-listed test fixture using desktop and mobile viewports. Wait for `GET /api/scans/{scan_id}` to report `completed`.
5. Run `POST /api/ai/analyze/{scan_id}`. For the screenshot-only audit, use `POST /api/ai/analyze/{scan_id}?screenshot_only=true`.
6. In the dashboard's Fix Review, use **Analyze screenshots with Vision AI**, inspect the structured finding and proposal, then use **Test AI fix in isolated browser**.
7. Preserve the API response, original screenshot, isolated after screenshot artifact, attempt log and final verdict. A successful isolated test is not the same as modifying the target's source files or opening a GitHub PR.

## Important correctness rules

- A completed scan is not a verified fix. `/api/verify_fix` now returns inconclusive unless an actual patch rescan is submitted.
- `/api/rescan` compares the follow-up metrics with the original scan identified by `scan_id`. If baseline evidence is absent or the issue type cannot be measured, it returns inconclusive.
- The AI healing endpoint only injects CSS into a disposable Playwright browser context. It does not write to the target source files, commit, push, or open a pull request.
- Model findings are probabilistic. Record misses, false positives and inconclusive outputs; never convert a model suggestion into a confirmed defect without checking its evidence.
- The configured URL allow-list is intended for the local prototype. Do not expose this scanner publicly without authentication, rate limits, stronger egress/SSRF controls and isolated execution.
