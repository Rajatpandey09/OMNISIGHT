# OmniSight — Complete Project Teaching Notes

> **Purpose of this document:** You should be able to read this end-to-end and walk into a technical review knowing exactly what the project does, how every piece works, what technology is used and *why*, and what decisions were made along the way.

---

## Part 1 — What Is OmniSight?

OmniSight is a **visual QA (Quality Assurance) automation tool** for websites. It automatically finds layout bugs — things like a button that disappears off the right edge of a phone screen, or content that makes the page scroll sideways when it shouldn't — and then uses an AI model to suggest and verify a CSS fix.

The whole point is to catch UI bugs that *look* fine in a desktop browser but break on a mobile screen, without a human having to manually check every device size.

### The problem it solves

Imagine you build a website. It looks perfect on your laptop. But on a phone it has a wide banner that makes the whole page scroll sideways. That's a **horizontal overflow** bug. Finding it manually means checking every page on every device. OmniSight automates this:

1. Take a screenshot of your page on desktop and mobile using a headless (invisible) browser
2. Measure the DOM (page structure) for known defect signatures
3. Show the screenshots and findings to an AI vision model
4. Have the AI suggest a CSS fix, test it in a throwaway browser, and verify it worked

---

## Part 2 — System Architecture (How All The Pieces Fit)

```
Browser (Chrome/Firefox)             Backend Server              Ollama (local AI)
        │                                   │                           │
        │  HTTP requests (fetch API)        │                           │
        ├──────────────────────────────────►│                           │
        │                                   │  Playwright               │
        │  HTML/CSS/JS frontend             │  (headless Chromium)      │
        │  - index.html                     │  captures screenshots     │
        │  - style.css                      │  measures DOM             │
        │  - script.js                      │                           │
        │  - api.js                         │  SQLite DB                │
        │  - config.js                      │  stores scan records      │
        │                                   │                           │
        │                                   │  POST /api/chat ─────────►│
        │                                   │  (vision analysis,        │
        │                                   │   patch suggestion,       │
        │                                   │   before/after verify)    │
        │◄──────────────────────────────────│◄──────────────────────────│
        │  JSON responses                   │  model answer (JSON)      │
```

### Key principle: separation of concerns

- **Frontend** (HTML/CSS/JS) — only displays things. Never talks to Ollama directly.
- **Backend** (Python/FastAPI) — does all the real work: browser automation, DB, AI calls.
- **Ollama** (local LLM server) — runs the AI models. Backend talks to it via HTTP.

---

## Part 3 — Technology Stack (What, Where, Why)

### 3.1 Python + FastAPI (Backend Framework)

**What it is:** FastAPI is a Python web framework for building APIs. An API is a set of URLs (called *endpoints*) that a frontend can call to get data or trigger actions.

**Why FastAPI specifically:**
- It's async (can handle multiple requests at the same time without waiting)
- Auto-generates interactive documentation at `/docs` — you can test every endpoint in the browser
- Uses Pydantic for data validation — if the frontend sends wrong data, FastAPI automatically rejects it with a clear error
- Much faster to write than older Python frameworks like Flask or Django

**Where it's used:** Every file ending in `.py` at the project root is part of the backend. `main.py` is the core app.

**Example endpoint:**
```python
@app.post("/api/scan")
async def create_scan(payload: ScanRequest):
    # payload is automatically validated by Pydantic
    # returns JSON
```

### 3.2 Playwright (Browser Automation)

**What it is:** Playwright is a library that lets Python code control a real web browser (Chromium/Chrome) without a visible window. It's called "headless" because there's no screen.

**Why Playwright specifically (not Selenium or Puppeteer):**
- Faster and more reliable than Selenium
- Native async support — fits FastAPI's async model
- Can capture full-page screenshots, intercept network requests, inject CSS into live pages
- Cross-browser support (Chromium, Firefox, WebKit)

**Where it's used:** `main.py` → `_run_playwright_scan_sync()`. Every scan triggers a Playwright session.

**What it does in OmniSight:**
1. Opens the target URL at two viewport sizes (1366×768 desktop, 390×844 mobile)
2. Takes a full-page screenshot → saved as a `.png` file in `artifacts/`
3. Runs JavaScript inside the page to measure: scroll width, button positions, hidden elements
4. Reports: `has_horizontal_overflow`, `buttons[].is_off_screen`, `hidden_controls[]`

**The sync-in-thread pattern:**
```python
# Playwright can't run inside FastAPI's async event loop directly on Windows
# Solution: run it synchronously in a thread pool
loop = asyncio.get_event_loop()
results = await loop.run_in_executor(None, _run_playwright_scan_sync, scan_id, url, viewports)
```
This is a common pattern when you have a blocking library (Playwright sync) that you need to run from an async context (FastAPI).

### 3.3 SQLAlchemy + SQLite (Database)

**What SQLite is:** A database that lives in a single file on disk (`omnisight.db`). No server needed. Perfect for a local/small-team tool.

**What SQLAlchemy is:** An ORM (Object-Relational Mapper). Instead of writing raw SQL (`SELECT * FROM scans WHERE id=5`), you write Python:
```python
record = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_id).first()
```
SQLAlchemy translates that to SQL automatically.

**Why not MongoDB or PostgreSQL?**
- SQLite requires zero setup — file already exists after first run
- For a demo/college project running on one machine, SQLite is perfect
- If you needed multi-server deployment or millions of records, you'd switch to Postgres (just change `DATABASE_URL` env var — SQLAlchemy handles the rest)

**The ScanRecord model** (`database.py`):
```python
class ScanRecord(Base):
    id           → auto-increment integer (internal DB ID)
    scan_id      → "scan-abc123" (string, what the frontend uses)
    url          → target website URL
    status       → "pending" | "processing" | "completed" | "failed" | "verified_resolved"
    viewports    → JSON: ["desktop", "mobile"]
    results      → JSON: list of viewport results with screenshots and metrics
    error        → error message if failed
    created_at   → timestamp
    completed_at → timestamp
```

**The status lifecycle:**
```
pending → processing → completed → verified_resolved
                    └→ failed
```

### 3.4 Pydantic (Data Validation)

**What it is:** A Python library that validates data shapes. You define what a request should look like, and Pydantic enforces it automatically.

**Why it matters:**
```python
class ScanRequest(BaseModel):
    url: str                                              # required
    scan_id: Optional[str] = None                        # optional
    viewports: Optional[List[str]] = ["desktop", "mobile"]
    sync: Optional[bool] = False
```
If the frontend sends `{"url": 123}`, Pydantic returns a `422 Unprocessable Entity` with a clear error message — you don't have to write validation code yourself.

**Version:** OmniSight uses Pydantic v2, which is significantly faster than v1.

### 3.5 Ollama (Local AI Model Server)

**What it is:** Ollama is a local server that runs AI language models on your own machine. Think of it like a local version of the ChatGPT API, but running entirely offline.

**Why local instead of cloud (OpenAI GPT-4V)?**
- Privacy — screenshots of your websites never leave your machine
- No API costs
- Works offline
- For a college project, no billing setup needed

**Models used:**

| Model | Size | Used for |
|---|---|---|
| `qwen2.5vl:3b` | 3.8B params, 3.2GB | Visual analysis — reads screenshots, compares before/after |
| `llama3.2:3b` | 3B params, 2GB | Text reasoning — generates CSS patch from structured finding description |

**Why two different models?**
This was an optimization made during the project. The heal loop originally used `qwen2.5vl:3b` for everything and took 107 seconds. The key insight: generating a CSS fix from a text description ("wide banner causes overflow") doesn't need vision capability. So we:
- Use `llama3.2:3b` (faster, text-only) for patch generation → 10 seconds
- Keep `qwen2.5vl:3b` (vision model) only for comparing before/after screenshots → 72 seconds
- Result: heal step went from 107s to 30s (72% faster)

**The VLM (Vision Language Model) explained:**
`qwen2.5vl:3b` is a *multimodal* model — it can process both text and images. When you send it a screenshot, it doesn't just see pixels — it understands what it's looking at: buttons, text, layout, overflow. The "3b" means 3 billion parameters (the numbers that define the model's knowledge). Bigger = smarter but slower/more RAM.

**How Ollama is called** (`vision/providers/ollama.py`):
```python
payload = {
    "model": "qwen2.5vl:3b",
    "stream": False,
    "format": "json",           # force structured output
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt, "images": [base64_screenshot]}
    ],
    "options": {"num_predict": 300, "temperature": 0.1}
}
```
`num_predict: 300` caps the output tokens — prevents the model from rambling. `temperature: 0.1` makes it more deterministic (less creative/random), which is what you want for JSON output.

### 3.6 Plain HTML + CSS + JavaScript (Frontend)

**Why not React/Vue?**
- Zero build step — open `index.html` and it works
- No `npm install` required
- For a team demo, plain JS is simpler to share
- Member 1 (Frontend Developer) can contribute without needing Node.js tooling knowledge

**Key files:**
- `index.html` — the entire page structure (single-page application, one HTML file)
- `style.css` — all styling, uses CSS custom properties (variables) for light/dark themes
- `script.js` — all UI logic: navigation, rendering issues/scans, button handlers
- `api.js` — API client class. All `fetch()` calls go through here. Never calls endpoints directly in script.js
- `config.js` — one line: sets the backend URL (`http://127.0.0.1:8001/api`)

**The API client pattern** (`api.js`):
```javascript
class ApiClient {
  constructor(baseUrl, timeout) { ... }

  async request(path, options) {
    // handles: AbortController timeout, JSON parsing, error mapping
  }

  // Named methods for each endpoint:
  async healScan(scanId, findingIndex, viewport, maxAttempts) {
    return this.request(`/ai/heal/${scanId}`, {
      method: "POST",
      body: { finding_index: findingIndex, viewport, max_attempts: maxAttempts },
      timeout: 300000   // 5 min — heal legitimately takes 30-120s
    });
  }
}
const OmniSightAPI = new ApiClient();  // singleton
```

**Why a singleton?** So you never accidentally have two API clients with different base URLs. `window.OmniSightAPI` is the one global instance everything uses.

**Cache-busting:** Every script tag has `?v=20261112c`. When you change a JS file, bump this version string and every browser downloads the fresh version instead of using its cached copy.

### 3.7 python-dotenv (.env file)

**What it is:** Loads environment variables from a `.env` file into `os.environ` when the app starts.

**Why use it:**
- Keeps secrets (API keys, model names, host URLs) out of source code
- Different environments (local dev vs production) can have different `.env` files
- Never commit `.env` to git (`.gitignore` excludes it)

**Current `.env`:**
```
VISION_PROVIDER=ollama,heuristic   # try ollama first, fall back to heuristic
VISION_MODEL=qwen2.5vl:3b          # VLM for visual analysis
PATCH_MODEL=llama3.2:3b            # text model for CSS generation
OLLAMA_HOST=http://127.0.0.1:11434
ALLOW_PUBLIC_TARGETS=true          # allow scanning any public website
FRONTEND_ORIGINS=http://127.0.0.1:5500,http://localhost:5500,...
```

---

## Part 4 — The Four Detection Systems

### 4.1 Playwright Metrics (System 1 — instant, no AI)

Runs automatically when a scan completes. Pure math, no model.

```python
# JavaScript executed inside the page by Playwright:
{
  scroll_width: document.documentElement.scrollWidth,     # e.g. 682px
  has_horizontal_overflow: scrollWidth > clientWidth,     # 682 > 390 = True
  buttons: [...].map(el => ({
    selector: el.id ? '#'+el.id : el.tagName,
    is_off_screen: el.getBoundingClientRect().right > window.innerWidth
  }))
}
```

If `has_horizontal_overflow = True`, the backend immediately creates an issue with:
- A template CSS fix (`html, body { overflow-x: clip }` + `.wide-banner { max-width: 100% }`)
- Source: `"playwright_metrics"`

This is why issues appear in the Issues tab immediately after a scan — no AI needed.

### 4.2 Heuristic Provider (System 2 — offline fallback)

A Python class (`vision/providers/heuristic.py`) that reads the metrics JSON and applies rules:
- `scroll_width > viewport_width` → `horizontal_overflow` finding
- `button.is_off_screen = True` → `offscreen_button` finding

This is the fallback when Ollama is unavailable. It can't see screenshots, only numbers.

### 4.3 VLM Analysis (System 3 — when you click "Analyze Screenshots")

`POST /api/ai/analyze/{scan_id}` → `vision/pipeline.py` → `vision/analyzer.py` → Ollama

The model receives:
- The PNG screenshot (base64 encoded)
- DOM metrics as JSON
- A snippet of the page's body HTML

It returns structured JSON:
```json
{
  "findings": [{
    "issue_type": "horizontal_overflow",
    "element": "div.wide-banner",
    "evidence": "650px banner causes scrolling on 390px viewport",
    "suggested_fix": "Add max-width: 100%; width: auto; to .wide-banner",
    "confidence": 0.9
  }],
  "cannot_determine": false
}
```

The `format: "json"` option in the Ollama API forces JSON output. The analyzer still validates and repairs the JSON in case the model outputs something slightly malformed (the `parse_model_json` function handles trailing commas, minor syntax errors).

### 4.4 Eval System (System 4 — accuracy measurement)

`eval/` folder. Runs the VLM against 9 known test cases and scores it:
- **TP** (true positive) — found a real bug
- **FP** (false positive) — reported a non-existent bug
- **FN** (false negative) — missed a real bug

Current score with `qwen2.5vl:3b` (screenshot-only mode): 3 TP, 0 FP, 1 FN, 1 error. The model misses `hidden_control` and can't output valid JSON for `low_contrast`.

---

## Part 5 — The Self-Healing Loop (The Core Feature)

This is the most sophisticated part of the project. The idea: not just detect bugs, but automatically suggest and verify a fix.

```
Finding (from VLM analysis)
    │
    ▼
PLAN: llama3.2:3b generates CSS patch
    "div.wide-banner { max-width: 100%; width: auto; }"
    (text reasoning only — no screenshot needed here)
    │
    ▼
EXECUTE: Playwright applies patch in a throwaway browser
    page.goto(original_url)
    page.add_style_tag(content=".wide-banner { max-width: 100%; }")
    page.screenshot() → heal_xxx_mobile.png
    re-measure DOM → overflow = False
    (source files NOT modified)
    │
    ▼
EVALUATE: qwen2.5vl:3b compares before + after screenshots
    before image (left) + after image (right) → stitched side by side
    model says: "fixed" / "not_fixed" / "inconclusive"
    │
    ▼
combine_verdicts(model_verdict, metrics_fixed, new_problems)
    "fixed" needs BOTH model AND metrics to agree
    model-only "fixed" → "inconclusive" (not enough evidence)
    │
    ▼
If not fixed: retry with feedback (up to 3 attempts)
    "earlier attempt '.wide-banner {width:100%}' did not fix it because..."
    │
    ▼
Return to human for approval
    human_approval_required = True
    source_page_modified = False
```

**Why human approval?** The CSS fix was only tested in a temporary browser — it was never written to any file. A human reviewer must look at the before/after screenshots, inspect the CSS, and explicitly click "Approve & verify" before anything is considered resolved.

**The two-signal requirement for `verified_resolved`:**

```python
def combine_verdicts(model_verdict, metrics_fixed, new_problems):
    if model_verdict == "fixed" and metrics_fixed == True and new_problems == "none":
        return "fixed", "the model and the metrics rescan both say fixed"
    if model_verdict == "fixed" and metrics_fixed is None:
        return "inconclusive", "model-only claim: metrics rescan needed"
    # ...
```

A single AI opinion isn't enough. The DOM measurement must also confirm the overflow is gone.

---

## Part 6 — Verification Persistence (The Gap That Was Fixed)

**The original bug:** After completing the full self-healing loop, the issue showed as "Verified" in the browser. But if you refreshed the page, it went back to "Detected". The verified state only lived in the browser's memory.

**Root cause:** The `get_issues` endpoint rebuilt issues from raw metrics on every request. No matter what the scan's DB status was, issues were always emitted with `state: "detected"`.

**The fix (three parts):**

1. `PATCH /api/scans/{scan_id}/verify` endpoint — explicitly persists verification state to DB:
```python
record.status = "verified_resolved"  # writes to omnisight.db
db.commit()
```

2. `/api/rescan` auto-writes when verification passes:
```python
if verification_state == "verified_resolved":
    baseline.status = "verified_resolved"
    db.commit()
```

3. `get_issues` checks the scan's status before emitting issues:
```python
scan_verified = r.status == "verified_resolved"
issue_state = "verified" if scan_verified else "detected"
# every issue from this scan gets state="verified"
```

Now after a successful verification: refresh the page → still shows "Verified". The dashboard "Verified Resolved" counter persists across restarts.

---

## Part 7 — Security Design

### SSRF Protection (Server-Side Request Forgery)

If a backend can be told to fetch any URL, an attacker could use it to access internal network resources (`http://192.168.1.1/admin`). OmniSight prevents this:

```python
def validate_target_url(url):
    # Only allow: http/https, standard ports, public IPs
    # Block: private ranges (10.x, 192.168.x, 127.x), credentials in URL
    local_demo = host in ALLOWED_DOMAINS
    public_site = ALLOW_PUBLIC_TARGETS and host resolves to a global IP
    if not (local_demo or public_site):
        raise HTTPException(400, "Target must be a public HTTP/HTTPS website")
```

### CSS Injection Safety

User-provided CSS patches go through `check_selector()` and `check_declarations()`:
```python
_BAD_CSS = re.compile(r"[<{}\\]|@import|url\(|expression\(|javascript:|behavior\s*:")
# Blocks: external file loads, JavaScript execution, CSS expressions
```

No patch containing `url()`, `@import`, or `javascript:` can reach a browser.

### No Automatic File Writes

Every response from the heal/verify loop includes:
```json
"source_page_modified": false
"human_approval_required": true
```
The only way source files change is if a developer manually applies the suggested CSS. OmniSight never writes to your project files.

### CORS (Cross-Origin Resource Sharing)

The backend only accepts requests from approved origins:
```python
FRONTEND_ORIGINS = ["http://127.0.0.1:5500", "http://localhost:5500", ...]
```
This prevents a random website from making API calls to your local backend.

---

## Part 8 — Project Structure Explained

```
omnisight-backend/
│
├── main.py              ← FastAPI app. All HTTP endpoints live here.
│                          Also contains: Playwright scan worker, SSRF validation,
│                          issue detection logic, dashboard/history endpoints.
│
├── database.py          ← SQLAlchemy setup. Defines ScanRecord model.
│                          init_db() creates the table if it doesn't exist.
│                          get_db() is a FastAPI dependency (injected per request).
│
├── vision_api.py        ← Vision AI + self-healing endpoints.
│                          /api/ai/analyze/{scan_id}  → VLM analysis
│                          /api/ai/heal/{scan_id}      → Plan/Execute/Evaluate loop
│                          /api/ai/verify/{scan_id}    → before/after VLM verdict
│
├── vision/              ← All AI-related Python code.
│   ├── factory.py       ← get_provider(mode) — picks which model to use
│   ├── pipeline.py      ← analyze_scan() — runs VLM on a scan's screenshots
│   ├── analyzer.py      ← analyze() — single viewport analysis, JSON parsing/repair
│   ├── patches.py       ← suggest_patches() + verify_fix() — patch generation
│   │                      and before/after comparison logic
│   ├── heal.py          ← heal() — the Plan/Execute/Evaluate retry loop
│   ├── prompts.py       ← All system prompts and user prompt builders
│   ├── schema.py        ← Pydantic models for VLM output validation
│   └── providers/
│       ├── base.py      ← Abstract VisionProvider class (interface definition)
│       ├── ollama.py    ← Real implementation — calls Ollama API
│       ├── heuristic.py ← Fallback — reads metrics, no model
│       ├── mock.py      ← Used in tests — returns fake responses
│       └── fallback.py  ← Tries providers in order until one succeeds
│
├── eval/                ← Accuracy measurement system.
│   ├── labelled_cases.json     ← 9 test cases with ground truth
│   ├── cases_data/             ← Pre-captured screenshots + metrics per case
│   ├── results/                ← run_1.json, run_2.json, run_3.json (scores)
│   └── summarize_runs.py       ← Comparison table across multiple runs
│
├── run_eval.py          ← CLI to run the evaluation benchmark
│
├── tests/               ← pytest test suite (155 tests)
│   ├── test_adapters.py    ← OllamaProvider unit tests
│   ├── test_analyzer.py    ← JSON parsing, finding schema tests
│   ├── test_backend.py     ← /api/scan, /api/scans HTTP contract tests
│   ├── test_pipeline.py    ← End-to-end pipeline with MockProvider
│   ├── test_patches.py     ← CSS safety checks, suggest_patches, verify_fix
│   ├── test_heuristic_fallback.py ← FallbackProvider, heuristic detection
│   └── test_no_secrets.py  ← Scans all source files for accidentally committed secrets
│
├── artifacts/           ← Screenshots saved here by Playwright.
│                          Named: {scan_id}_{viewport}.png
│                          Served at: /artifacts/{filename} (StaticFiles mount)
│
├── omnisight.db         ← SQLite database file. All scan records stored here.
│
├── index.html           ← Frontend — single HTML page (SPA)
├── style.css            ← All CSS, light + dark theme via CSS variables
├── script.js            ← All UI logic, rendering, button handlers
├── api.js               ← API client class (all fetch() calls)
├── config.js            ← Backend URL config (one line)
│
├── .env                 ← Local config (never committed to git)
├── .env.example         ← Template for new developers
├── requirements.txt     ← Python dependencies with pinned versions
└── pytest.ini           ← Test configuration
```

---

## Part 9 — API Endpoint Reference

| Method | Path | What it does |
|---|---|---|
| `GET` | `/health` | Backend alive check |
| `GET` | `/api/targets` | List demo page URLs for the scan form |
| `POST` | `/api/scan` | Start a new scan (async by default, `sync:true` for immediate) |
| `GET` | `/api/scans` | All scan history (newest first) |
| `GET` | `/api/scans/{scan_id}` | Single scan status + results |
| `DELETE` | `/api/scans/{scan_id}` | Delete scan + its artifacts |
| `PATCH` | `/api/scans/{scan_id}/verify` | Persist verified state to DB |
| `GET` | `/api/issues` | All detected issues across all scans |
| `GET` | `/api/dashboard` | Metric card totals |
| `POST` | `/api/rescan` | Apply CSS patch + follow-up Playwright scan |
| `POST` | `/api/verify_fix` | Alias verify endpoint for frontend |
| `POST` | `/api/ai/analyze/{scan_id}` | VLM analysis of screenshots |
| `POST` | `/api/ai/heal/{scan_id}` | Plan→Execute→Evaluate self-healing loop |
| `POST` | `/api/ai/verify/{scan_id}` | VLM before/after comparison |
| `POST` | `/api/approve_fix` | Record human approval (no file changes) |
| `POST` | `/api/reject_fix` | Record human rejection |
| `GET` | `/api/compare` | Diff two scans |
| `GET` | `/api/report/{scan_id}` | Export scan as JSON |
| `GET` | `/artifacts/{filename}` | Serve screenshot PNG files |

---

## Part 10 — Data Flow: One Complete Scan Walkthrough

**Scenario:** You paste `http://localhost:5500/test-pages/bug_overflow.html` into the scan form and click Run Scan.

```
1. Frontend (script.js)
   OmniSightAPI.createScan({ url: "http://...", scan_id: "scan-abc123", viewports: ["desktop","mobile"] })
   → POST /api/scan

2. Backend (main.py) validates URL, creates ScanRecord(status="pending"), returns 202 Accepted
   {scan_id: "scan-abc123", status: "pending", message: "Poll /api/scans/scan-abc123"}

3. Frontend polls GET /api/scans/scan-abc123 every 3 seconds

4. Background worker (run_scan_worker) in a thread pool:
   _run_playwright_scan_sync("scan-abc123", url, ["desktop","mobile"])
     → Chromium opens at 1366×768
     → page.goto(url, wait_until="domcontentloaded")
     → page.screenshot(path="artifacts/scan-abc123_desktop.png")
     → page.evaluate(JS metrics) → {has_horizontal_overflow: False, ...}
     → page.close()
     → Chromium opens at 390×844
     → screenshot → "artifacts/scan-abc123_mobile.png"
     → metrics → {has_horizontal_overflow: True, scroll_width: 682}
     → page.close()
   → ScanRecord.status = "completed", ScanRecord.results = [desktop_result, mobile_result]
   → db.commit()

5. Frontend poll returns {status: "completed"} → shows scan in history

6. User clicks on issue "Horizontal Overflow Detected (Mobile)" in Issues tab
   → GET /api/issues
   Backend reads ScanRecord.results, sees has_horizontal_overflow=True in mobile viewport
   Creates issue with:
     - title: "Horizontal Overflow Detected (Mobile)"
     - suggested_css: "html, body { overflow-x: clip; } .wide-banner { max-width: 100% }"
     - before_screenshot: "http://127.0.0.1:8001/artifacts/scan-abc123_mobile.png"
     - source: "playwright_metrics"  ← no AI involved yet

7. User clicks "Analyze screenshots with Vision AI →"
   → POST /api/ai/analyze/scan-abc123
   Backend loads scan-abc123_mobile.png, sends to qwen2.5vl:3b via Ollama
   Model returns: {issue_type: "horizontal_overflow", element: "div.wide-banner",
                   suggested_fix: "Add max-width: 100%; to .wide-banner", confidence: 0.9}
   Frontend updates issue with AI finding, shows "Proposed" badge

8. User clicks "Test AI fix in isolated browser →"
   → POST /api/ai/heal/scan-abc123 {finding_index:0, viewport:"mobile"}
   Backend:
     PLAN: llama3.2:3b → ".wide-banner { max-width: 100%; width: auto; }"
     EXECUTE: Playwright opens page, injects CSS, screenshots → heal_xxx_mobile.png
              metrics → overflow=False ← patch worked!
     EVALUATE: qwen2.5vl:3b compares before+after → "fixed"
     combine_verdicts("fixed", True, "none") → "fixed"
   Returns: {status:"fixed", final_css:".wide-banner{max-width:100%}", human_approval_required:true}

9. User clicks "Approve & verify proposed CSS"
   → POST /api/rescan {url, css_patch, scan_id:"scan-abc123", issue_type:"horizontal_overflow"}
   Backend applies patch, rescans, finds overflow=False
   → verification_state = "verified_resolved"
   → Writes: original scan status = "verified_resolved" (persisted to DB ✓)

   → POST /api/ai/verify/scan-abc123 {rescan_id, viewport:"mobile", issue_type:"horizontal_overflow"}
   Model compares screenshots → verdict: "fixed", confidence: 0.9

   → PATCH /api/scans/scan-abc123/verify {verification_state:"verified_resolved"}

10. Frontend updates issue badge → "Verified" (green)
    Dashboard: "Verified Resolved" counter = 1
    After page refresh: still shows "Verified" (persisted in DB ✓)
```

---

## Part 11 — Key Design Decisions & Why

| Decision | Why |
|---|---|
| SQLite instead of Postgres/MongoDB | Zero setup, single file, sufficient for one-machine demo |
| Async FastAPI + sync Playwright in thread pool | Playwright's sync API is simpler but blocks; thread pool lets FastAPI stay responsive |
| Two-signal verification (model + metrics) | AI alone can hallucinate; deterministic metrics catch false "fixed" claims |
| `llama3.2:3b` for patch generation | Doesn't need vision — 10× faster than the VLM for this text-only task |
| Human approval gate before any file change | Safety — AI suggestions are proposals, not commands |
| `num_predict` caps on Ollama calls | Cuts inference time significantly; patch JSON only needs ~300 tokens |
| `temperature: 0.1` for model calls | More deterministic JSON output; less creative variance |
| `format: "json"` in Ollama payload | Forces structured output; analyzer still validates and repairs it |
| `FallbackProvider([ollama, heuristic])` | If Ollama is down or slow, heuristic still provides metric-based findings |
| Screenshot files on disk, not in DB | Disk is 5× faster for writes; `StaticFiles` serves them with zero Python overhead |
| Cache-busting version strings (`?v=20261112c`) | Browser always loads the latest JS/CSS without manual cache clearing |

---

## Part 12 — How To Run The Project

```bash
# 1. Install Python dependencies
pip install -r requirements.txt
playwright install chromium

# 2. Install and start Ollama (from ollama.ai)
ollama pull qwen2.5vl:3b
ollama pull llama3.2:3b

# 3. Configure environment
cp .env.example .env
# edit .env if needed

# 4. Start the backend (terminal 1)
uvicorn main:app --host 127.0.0.1 --port 8001

# 5. Serve the frontend (terminal 2)
python -m http.server 5500

# 6. Open in browser
# http://127.0.0.1:5500/index.html

# 7. Run tests
PYTHONPATH=. pytest -q

# 8. Run accuracy evaluation
PYTHONPATH=. python run_eval.py --provider ollama --timeout 60
```

---

## Part 13 — Glossary

| Term | Meaning |
|---|---|
| **API** | Application Programming Interface — a set of URLs a program can call |
| **Endpoint** | One specific URL in an API (`/api/scan`) |
| **Async** | Non-blocking — the server can handle other requests while waiting |
| **ORM** | Object-Relational Mapper — Python objects that represent DB rows |
| **Headless browser** | A browser with no visible window, controlled by code |
| **DOM** | Document Object Model — the in-memory tree structure of an HTML page |
| **VLM** | Vision Language Model — an AI that understands both text and images |
| **Inference** | Running an AI model to get an answer (the slow/expensive part) |
| **Token** | A chunk of text the model processes (~4 characters on average) |
| **num_predict** | Max tokens the model will generate in one response |
| **CORS** | Cross-Origin Resource Sharing — browser security rule about which origins can call an API |
| **SSRF** | Server-Side Request Forgery — attack where a server is tricked into fetching internal URLs |
| **SQLite** | Serverless database in a single file |
| **Heuristic** | A rule-based approach (no ML/AI), e.g. "if scrollWidth > viewportWidth then overflow" |
| **TP/FP/FN** | True Positive / False Positive / False Negative — accuracy metrics |
| **Pydantic** | Python data validation library |
| **BackgroundTasks** | FastAPI feature that runs code after returning a response |
| **Thread pool executor** | Runs blocking code on worker threads without blocking the main async loop |
| **base64** | Encoding that converts binary (like a PNG image) to plain text so it can go in JSON |
| **Cache-busting** | Adding a version query string to static files to force browsers to re-download |
