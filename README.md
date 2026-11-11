# OmniSight

**A multimodal UI quality-assurance system that scans web pages, finds visual bugs with a vision-language model, proposes controlled fixes, and verifies them with a rescan.**

![Status](https://img.shields.io/badge/status-mid--project-orange)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688)
![Playwright](https://img.shields.io/badge/automation-Playwright-45ba4b)

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Vision AI Module](#vision-ai-module)
- [Testing and QA](#testing-and-qa)
- [Security](#security)
- [Project Status](#project-status)
- [Limitations](#limitations)
- [Roadmap](#roadmap)
- [Team](#team)

---

## Overview

Visual bugs such as horizontal overflow, overlapping text, off-screen buttons and low contrast are easy for humans to see and hard for traditional tests to catch. OmniSight combines browser automation with a vision-language model (VLM) to act like a human tester:

1. **Scan** a page at desktop and mobile sizes.
2. **Detect** visual defects from screenshots and layout metrics.
3. **Propose** a fix, never applied automatically.
4. **Approve** the fix with a human in the loop.
5. **Verify** by rescanning and comparing before and after.

OmniSight is designed to **report uncertainty honestly**. A finding is either `detected` or `inconclusive`, and nothing is marked resolved unless a second scan supports it.

## How It Works

```
Test page
   │
   ▼
FastAPI scan request  ──►  Playwright (desktop 1366×768 + mobile 390×844)
                                   │
                                   ▼
                        Screenshots + layout metrics
                                   │
                                   ▼
                  Vision AI module (schema-validated JSON)
                                   │
                                   ▼
                     Finding + proposed CSS fix
                                   │
                                   ▼
                          Human approval
                                   │
                                   ▼
                  Fix applied in an isolated local copy
                                   │
                                   ▼
                  Second scan + QA comparison
                                   │
                                   ▼
                    Dashboard status and evidence
```

**Fix lifecycle:**
`detected → fix_proposed → awaiting_approval → applied → verified_resolved / verification_failed / inconclusive`

## Architecture

| Layer | Responsibility |
|---|---|
| **Frontend dashboard** | Scan form, metric cards, issue details, evidence panels, fix review |
| **API gateway (FastAPI)** | Routing, CORS, request-ID and timing middleware, input validation |
| **Security guard** | Domain allow-list to prevent SSRF |
| **Browser automation (Playwright)** | Headless Chromium, dual viewports, screenshots, DOM metrics |
| **Artifact storage** | Screenshots stored locally under `artifacts/`, keyed by `scan_id` |
| **Vision AI module** | Prompt building, model providers, JSON schema validation |
| **QA and evaluation** | Reproducible faulty pages, labelled cases, verification rules |

Private API keys never reach the browser. The backend is decoupled from AI vendor secrets.

## Tech Stack

| Area | Tools |
|---|---|
| Backend | Python, FastAPI, Uvicorn, Pydantic, SQLAlchemy, SQLite |
| Browser automation | Playwright (async API), headless Chromium |
| Task Processing | FastAPI BackgroundTasks (Asynchronous 202 Accepted + Polling) |
| Vision AI | Ollama (`gemma4:31b-cloud`), JSON schema validation |
| Frontend | HTML, CSS, JavaScript |
| Testing | pytest, HTML/CSS faulty test pages, JSON and Markdown evidence |
| Collaboration | Git and GitHub, branch-per-member workflow |

## Project Structure

> Adjust folder names to match the repository.

```
omnisight/
├── backend/                 # FastAPI + Playwright scanner
│   ├── test_backend.py      # pytest: health checks, SSRF guard
│   └── artifacts/           # Stored screenshots (git-ignored)
├── vision/                  # Vision AI module
│   ├── pipeline.py          # Reads scans, shrinks screenshots
│   ├── prompts.py           # Builds compact, injection-safe prompts
│   └── analyzer.py          # Parses and validates model output
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── eval/
│   ├── labelled_cases.json  # Ground-truth labels
│   └── cases_data/<case_id>/{screenshot.png, metrics.json}
├── test-pages/              # Reproducible faulty HTML pages
├── test_matrix.md           # What to test and acceptance criteria
├── test_results.md          # Observations and verification status
├── .env.example
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/) with an active sign-in (for the cloud vision model)
- Git

### Installation

```bash
git clone https://github.com/Rajatpandey09/OMNISIGHT.git
cd OMNISIGHT

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium
```

### Configuration

Copy the example environment file and edit it:

```bash
cp .env.example .env
```

```env
VISION_PROVIDER=ollama
VISION_MODEL=gemma4:31b-cloud
```

> **Never commit `.env` or API keys.** The repository includes a secrets check.

### Run the backend

```bash
uvicorn main:app --reload
```

Interactive API docs are available at `http://localhost:8000/docs`.

### Run a scan

```bash
curl -X POST http://localhost:8000/api/scan \
  -H "Content-Type: application/json" \
  -d '{"url": "http://localhost:5500/test-pages/horizontal_overflow.html", "scan_id": "demo-001"}'
```

### Run the frontend

Open `frontend/index.html` in a browser, or serve it locally:

```bash
python -m http.server 5500
```

## Local demo: evidence and review behaviour

The root FastAPI application stores Playwright viewport screenshots in `artifacts/` and serves them at `/artifacts/<filename>`. The live issue API returns `before_screenshot` / `screenshot_url` fields that the Fix Review page can display. It also returns a metric-based CSS starting point in `suggested_css` for the two currently metric-detected issue classes (horizontal overflow and off-screen buttons). These are review suggestions, not automatically applied patches and not proof that the issue is fixed.

The approval endpoint acknowledges reviewer approval only; it does not modify the target website. A fix must be applied in an isolated copy and then checked with a follow-up scan before it can honestly be described as verified. The current root scanner's automated metric detections cover horizontal overflow and off-screen buttons. Other supplied defect pages are useful demo fixtures, but their detection should not be claimed unless a corresponding finding is actually returned by the running backend.

For the local demo, start the frontend from the repository root on port 5500 and the FastAPI service on port 8000. Keep Ollama running locally for the Q&A assistant. The Q&A endpoint uses scan metrics and stored scan metadata; it does not currently inspect screenshot pixels as part of its answer context.

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Service info and active role status |
| `GET` | `/health` | Health check and database connection status |
| `POST` | `/api/scan` | Initiate async browser scan across desktop & mobile (returns `202 Accepted`) |
| `GET` | `/api/scans/{scan_id}` | Poll scan status, execution progress, and extracted metrics |
| `GET` | `/api/scans` | Retrieve persistent history of all executed scans from SQLite |
| `DELETE` | `/api/scans/{scan_id}` | Delete scan record and associated screenshot artifacts |
| `POST` | `/api/rescan` | Inject proposed CSS patch and re-evaluate layout to verify resolution |
| `POST` | `/api/verify_fix` | Verify fix resolution state for frontend dashboard |
| `GET` | `/api/artifacts` | List all stored screenshot artifacts with file sizes |
| `DELETE` | `/api/artifacts/clean` | Delete all generated screenshot files to free local disk space |

**Scan request:**

```json
{ 
  "url": "http://localhost:5500/test-pages/horizontal_overflow.html", 
  "scan_id": "demo-001",
  "viewports": ["desktop", "mobile"]
}
```

The response returns immediately with `202 Accepted` and a polling URL:

```json
{
  "scan_id": "demo-001",
  "status": "pending",
  "url": "http://localhost:5500/test-pages/horizontal_overflow.html",
  "viewports": ["desktop", "mobile"],
  "message": "Scan scheduled in background. Poll /api/scans/{scan_id} for progress.",
  "results": []
}
```

Once completed, polling `GET /api/scans/{scan_id}` returns metadata, screenshot file paths, and deep DOM layout metrics (scroll dimensions, horizontal overflow, button bounding boxes, text content, and hidden-control state) for each viewport.

## Vision AI Module

The vision module turns screenshots and page metrics into **structured, schema-validated findings**. It returns JSON only. **Nothing the model writes is ever executed automatically.**

### Processing steps

1. `pipeline.py` reads the scan result and shrinks each screenshot.
2. `prompts.py` builds a compact prompt. Text inside screenshots or HTML is treated as **untrusted page content, never instructions**. HTML is cleaned (scripts and comments removed) and truncated to 4000 characters.
3. A **provider chain** calls the model: Ollama, then heuristic, then mock. If one fails, the next answers, and the result records which one did.
4. `analyzer.py` parses the JSON, validates it against the schema, labels failures, and never crashes.

### Providers

| Provider | Description |
|---|---|
| **Ollama** | Real vision model (`gemma4:31b-cloud`). Runs on Ollama's servers, so screenshots leave your machine |
| **Heuristic** | Reads metrics only. Not a vision model, and cannot run in screenshot-only mode |
| **Mock** | Fake provider for automated tests |

### Output

Written to `analysis.json`.

- **Outcomes:** `ok`, `no_credentials`, `provider_error`, `invalid_output`, `input_error`
- **Finding status:** `detected` or `inconclusive`, so uncertainty is never shown as a pass

### Vision audit (screenshot-only mode)

Sends the image only, with no metrics or HTML, to test what the model can see on its own:

```bash
python run_eval.py --provider ollama --screenshot-only --timeout 300
```

### Evaluation

The evaluation runner compares findings with `eval/labelled_cases.json` and reports counts of:

- **TP:** real defect detected
- **FP:** defect reported that is absent
- **FN:** real defect missed
- **Inconclusive:** insufficient evidence to decide

Results are reported as counts (for example, "found X of Y seeded bugs, Z false alarms"), not as accuracy percentages.

### Week 3 and 4 additions

| Module | What it does |
|---|---|
| `vision/patches.py` | Suggests small CSS fixes as validated JSON and checks BEFORE/AFTER screenshots. Unsafe CSS is dropped, the model never chooses the file path, and nothing is executed. |
| `vision/heal.py` | Self-healing loop: suggest a fix, apply it to a local copy (supplied by the caller), rescan, verify, retry up to 3 times. A fix counts as fixed only when the model and a metrics rescan agree. |
| `vision/crop.py`, `vision/chunk.py` | Crop to the problem area for a close-up check, tile tall pages, and measure what a crop saves. |

Command line tools: `run_patches.py`, `run_verify.py`, `run_crop.py` and `run_savings.py` (each accepts `--help`).

## Testing and QA

```bash
pytest
```

The suite covers API health checks, SSRF guard behaviour, and the vision module (analysis pipeline, patch suggestions, self-healing loop, cropping and evaluation).

### QA test cases

| Case | Purpose |
|---|---|
| Horizontal overflow | Page wider than the mobile viewport (390px viewport, 920px document) |
| Off-screen button | Actionable button stays visible |
| Overlapping text | Elements whose text overlaps |
| Hidden control | Control not visible or usable |
| Low contrast *(optional)* | Text and background readability |
| Clean page | False-positive check on a defect-free page |

### Verification rules

- Record the original defect, viewport and before screenshot.
- Require human approval before any change is applied.
- Rescan the same page and viewport, and also check desktop for new problems.
- Mark `verified_resolved` **only** when the second scan supports it.

## Security

- **SSRF protection:** only allow-listed domains (`localhost`, `127.0.0.1`, `example.com`) can be scanned. Others return HTTP 400.
- **No automatic execution:** model output is validated JSON and is never run.
- **Prompt-injection guard:** page text is treated as data, not instructions.
- **Secrets hygiene:** API keys stay server-side and are never committed. A secrets check runs in the test suite.
- **Privacy note:** the cloud vision model sends screenshots to Ollama's servers. It is cloud-hosted, not local or private.

## Project Status

OmniSight is in active development (mid-project review stage).

| Component | Status |
|---|---|
| FastAPI backend and dual-viewport Playwright scanning | Built |
| SSRF guard, retries, request tracing, artifact storage | Built |
| Vision pipeline, provider chain, analyzer, evaluation runner | Built, unit-tested |
| QA test pages and manual evidence | Built (manual reproduction confirmed) |
| Dashboard layout and scan form | In progress |
| Vision audit | Done on 9 synthetic pages (screenshot-only, 3 runs): 4 of 5 seeded bugs found in every run, hidden control missed, no false alarms on 4 clean pages. **Real screenshots pending** |
| End-to-end scan from dashboard | **Pending** |
| Fix proposal and before/after verification (vision module) | Built, unit-tested; real-model run pending |
| Applying fixes in the browser, GitHub pull requests, dashboard approval | **Pending** |

> Manual reproduction of a bug is **not** proof of automated detection or self-healing. Features are marked complete only after their behaviour has been verified.

## Limitations

- The vision audit ran on nine synthetic (drawn) pages, not real browser captures, and the prompt rules were tuned after seeing those pages fail. Results are counts on a small set, not accuracy.
- A hidden element is not drawn in a screenshot, so a pure screenshot audit is expected to miss a hidden submit button. Metrics from the scanner are needed to catch it.
- The cloud model sends screenshots off-device.
- The domain allow-list limits scanning to a small set of hosts.

## Roadmap

- [x] **Week 1:** Finding schema, provider interface, FastAPI scaffolding, Playwright dual-viewport scanning
- [x] **Week 2:** Screenshot-to-JSON pipeline, Ollama adapter, fallback chain, evaluation runner
- [x] **Mid-review:** Vision audit on synthetic pages (real screenshots still pending)
- [ ] **Week 3:** Patch suggestions and self-healing loop with before/after verification (built in the vision module, real-model run pending); applying fixes in the browser and GitHub pull requests (pending)
- [ ] **Week 4:** Screenshot cropping and tiling (built, real-model run pending); QA dashboard to approve or reject fixes (pending); final evaluation table

## Team

| Member | Role | Responsibility |
|---|---|---|
| Member 1 (Rajat) | Frontend Developer | Dashboard UI, responsive design, API integration |
| Member 2 (Priyanshu Singh) | Backend and Browser Automation | FastAPI, Playwright, security, artifacts |
| Member 3 | Vision AI / ML Engineer | Vision pipeline, prompts, providers, evaluation |
| Member 4 | QA, Integration and Self-Healing | Test cases, ground truth, fix verification |

## Contributing

1. Create a branch per member or feature.
2. Run `git status` before committing and use descriptive commit messages.
3. Run `pytest` and re-test API integration after shared changes.
4. Open a pull request and merge only after team review.

## License

Add a license here (for example, MIT) or state that the project is for academic use.
