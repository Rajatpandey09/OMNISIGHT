# OmniSight Backend — Agent Context & Project Blueprint

## 📋 1. Project Overview
* **Project Name:** OmniSight (`omnisight-backend`)
* **Repository:** `Rajatpandey09/OMNISIGHT`
* **Core Purpose:** Production-grade FastAPI backend service for multimodal UI auditing, cross-viewport layout verification, and resilient browser automation using Playwright.
* **Primary Engineer / Author:** Priyanshu Singh (Backend & Browser Automation Engineer)
* **Team Context (Infotact Solutions):**
  * **Member 1 (Frontend Developer):** React QA dashboard (UI visualization, fix review, screenshot comparisons).
  * **Member 2 (Backend & Browser Automation Engineer - Priyanshu Singh):** Playwright scanner, headless capture, DOM metric extraction, resilient navigation, and API service.
  * **Member 3 (Vision AI / ML Engineer):** Multimodal VLM analysis (LLaVA / GPT-4V), layout anomaly interpretation, CSS patch suggestions.
  * **Member 4 (QA, Integration & Self-Healing):** Reproducible defect pages, end-to-end patch verification, regression tests.

---

## 🛠️ 2. Tech Stack & Dependencies
* **Framework:** FastAPI (Python) with Pydantic v2 data validation.
* **Browser Automation:** Playwright (`async_api`) for headless Chromium automation.
* **Testing:** `pytest`, `pytest-asyncio`, `respx`, `hypothesis` (40 comprehensive unit/integration test suites).
* **Runtime/Environment:** Python 3.13 on macOS (Apple Silicon M2).
* **Security & Observability:** Custom request-id middleware (`X-Request-ID`), process time tracking headers (`X-Process-Time`), structured logging, and SSRF domain whitelisting (`ALLOWED_DOMAINS`).

---

## 📂 3. Repository Directory Structure
```text
omnisight-backend/
├── main.py                # Core FastAPI app, routes, SSRF checks, and Playwright automation logic
├── database.py            # (Upcoming) SQLAlchemy ORM models and SQLite session configuration
├── artifacts/             # Local storage directory for generated viewport screenshots (.png)
├── tests/                 # Full pytest suite (adapters, analyzer, backend, eval, main, pipeline)
│   ├── test_adapters.py
│   ├── test_analyzer.py
│   ├── test_backend.py
│   ├── test_eval.py
│   ├── test_heuristic_fallback.py
│   ├── test_labelled_cases.py
│   ├── test_main.py       # Contract tests for /api/scan, /api/scans, and viewports
│   ├── test_no_secrets.py
│   ├── test_pipeline.py
│   └── test_screenshot_only.py
├── requirements.txt       # Project dependencies
└── README.md              # Documentation & API contracts
```

---

## ⚡ 4. Current State & Milestone

* **Test Status:** 100% passing (`12/12 test_backend unit/integration tests green`, `40/40 full project tests green`). Note: Run tests using `PYTHONPATH=. pytest`.
* **Current Features Implemented:**
  * **Database Persistence (`database.py`):** Fully migrated to SQLAlchemy ORM with SQLite backend (`ScanRecord` model, automatic table initialization, schema tracking).
  * **Asynchronous Background Processing:** Decoupled browser automation from HTTP requests using FastAPI `BackgroundTasks`, returning `202 Accepted` immediately.
  * **Status Polling Endpoints:** Dedicated `/api/scans/{scan_id}` status lookup endpoint allowing frontend polling of async scan progress (`pending` -> `processing` -> `completed` / `failed`).
  * **Scan History Tracking:** Persistent `/api/scans` endpoint backed by SQLite query ordered by recency.
  * **Simultaneous Multi-Viewport Capture:** Captures desktop (1366x768) and mobile (390x844) viewports in a single scan request.
  * **Deep DOM Metric Extraction:** Evaluates button boundaries (`getBoundingClientRect`), off-screen elements, hidden controls, and horizontal overflows.
  * **Self-Healing Verification Loop:** `/api/rescan` and `/api/verify_fix` endpoints to inject suggested CSS patches into the live page and verify defect resolution without regressions.
  * **Resilient Navigation:** Exponential backoff retry mechanism (`navigate_with_retry`) to handle flaky network conditions.
  * **Security Guards:** SSRF protection whitelisting local/safe domains, returning explicit `400 Bad Request` for unauthorized targets.
  * **Artifact Lifecycle Management:** `/api/artifacts` and `/api/artifacts/clean` endpoints.

---

## 🚀 5. Immediate Next-Day Roadmap & Action Items

The backend is now persistent and asynchronous. Upcoming engineering milestones:

1. **VLM Patch Integration (Week 3 Collaboration with Member 3 & Member 4):**
   * Wire the `/api/rescan` endpoint to accept Vision AI's suggested CSS patches directly from the triage pipeline.
   * Verify that layout anomalies (such as horizontal overflow and off-screen buttons) are marked as `verified_resolved` automatically.

2. **GitHub PR Automation Preparation:**
   * Prepare automated patch PR generation utility using PyGithub to commit verified CSS patches to feature branches.

3. **Performance Optimization:**
   * Implement selective screenshot cropping/element bounding-box extraction to reduce payload sizes for the VLM agent.

---

## ⚙️ 6. Quick Development Commands

* **Run Test Suite:**
  ```bash
  PYTHONPATH=. pytest
  ```

* **Run Local Development Server:**
  ```bash
  uvicorn main:app --reload --host 127.0.0.1 --port 8000
  ```
