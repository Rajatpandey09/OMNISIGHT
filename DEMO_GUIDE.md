# OmniSight — Live Demo Guide

## Prerequisites

Before starting, ensure the following are installed and ready:

| Requirement | Check |
|---|---|
| Python 3.10+ | `python --version` |
| Playwright Chromium | Installed automatically |
| Ollama | Running at `http://localhost:11434` |
| Vision model pulled | `ollama pull qwen2.5vl:3b` |

---

## Quickstart (3 steps)

### Step 1 — Start the backend

```powershell
# From the project root directory
.\.venv312\Scripts\uvicorn.exe main:app --host 127.0.0.1 --port 8000 --reload
```

### Step 2 — Serve the frontend (optional — for local test pages)

Open a second terminal:

```powershell
.\.venv312\Scripts\python.exe -m http.server 5500
```

### Step 3 — Open the application

Open `index.html` directly in a browser, **or** navigate to:
```
http://127.0.0.1:5500/index.html
```

The dashboard loads automatically and connects to the backend at `http://127.0.0.1:8000`.

---

## Demo Walkthrough

### 1. Dashboard Overview

After launch, the dashboard shows:
- **Total scans** — number of scan runs recorded
- **Issues found** — total detected visual and functional issues
- **Verified resolved** — issues confirmed fixed by a follow-up scan
- **Need attention** — open issues requiring human review
- **Recent scans** — last 5 scan runs
- **Priority issues** — top-severity open issues

---

### 2. Scanning Your Own Website

Navigate to **New scan** in the left sidebar.

**To scan any public website:**
1. Leave the dropdown on "— Enter your own URL below —"
2. Type your URL in the "Or enter any public website URL" field
   - Example: `https://example.com`
   - Example: `https://your-website.com`
3. Select viewports: Desktop (1366×768) and/or Mobile (390×844)
4. Click **Run scan ↗**

**To scan a local bug page (requires the Python HTTP server on port 5500):**
1. Select a pre-configured target from the dropdown
   - e.g., "Bug: Horizontal Overflow" or "Bug: Off-Screen Button"
2. Click **Run scan ↗**

The scan runs Playwright in the background — screenshots are captured automatically. Progress updates appear in the form. When done, the app navigates to the Issues page if issues were found.

---

### 3. Viewing Screenshots and Issues

Navigate to **Issues** in the sidebar.

Each issue shows:
- Title and description
- Severity (Critical / High / Medium / Low)
- Viewport (desktop / mobile)
- Detection source (playwright_metrics / playwright_console / etc.)
- Screenshot evidence badge
- Current state (Detected / Proposed / Verified / Failed)

Click **Review issue →** on any issue to open the detailed review page.

---

### 4. Issue Review and Self-Healing

The **review page** shows:
- Full-page screenshot (before fix)
- Issue description and evidence
- Suggested CSS fix
- Verification outcome

**To trigger AI-assisted self-healing:**
1. Click **Analyze screenshots with Vision AI →**
2. Wait for the Ollama model to analyze the screenshot
3. If a finding is returned with a suggested fix, click **Test AI fix in isolated browser →**
4. The fix is tested in a disposable Playwright browser — your website is NOT modified
5. If the test passes, click **Approve & verify proposed CSS**
6. A follow-up scan confirms whether the issue is resolved

**Expected result for horizontal overflow bug:**
```
Isolated browser result: fixed
Verification: verified_resolved
```

---

### 5. AI Q&A Assistant

Click the **"Ask OmniSight AI"** button (bottom-right of the screen), or click **AI Q&A** in the sidebar.

1. Select a completed scan from the dropdown
2. Ask a question about the scan results

**Example questions:**
- "What are the biggest problems on this page?"
- "Why does the mobile layout overflow?"
- "Which issue should I fix first?"
- "Explain the console errors found"
- "Suggest a CSS fix for the offscreen button"

**To analyze an uploaded screenshot:**
1. Use the file upload input in the Q&A panel
2. Select a PNG/JPG/WebP screenshot (max 8 MB)
3. Ask a question about what you see

---

### 6. Scan History and Comparison

Navigate to **Scan history** in the sidebar.

- View all past scans with status and issue counts
- Click **View →** to see detailed screenshots and metrics for any scan
- Click **Export ↓** to download a JSON report

**To compare two scans:**
1. Scroll down to the "Compare Scans" section
2. Select Scan A and Scan B from the dropdowns
3. Click **Compare scans →**

The comparison shows:
- 🔴 New issues (appeared in scan B but not A)
- ✅ Resolved issues (in A but not B)
- 🔄 Recurring issues (in both)

---

### 7. Exporting Reports

From any completed scan:
1. In **Scan history**, click **Export ↓** next to any scan
2. Or, while reviewing an issue, click **Export report ↓** at the top

The export downloads as `omnisight-report-{scan_id}.json` containing:
- Scan metadata (URL, timestamps, viewports)
- All viewport captures with screenshot URLs
- Complete issue list with evidence
- Summary statistics (high/medium/low counts)

---

## Supported Issue Types

| Type | Detected Via | Description |
|---|---|---|
| `horizontal_overflow` | Playwright DOM metrics | Page content wider than viewport |
| `offscreen_button` | Playwright DOM metrics | Interactive button outside visible area |
| `broken_image` | Playwright DOM metrics | Image with zero natural dimensions |
| `console_error` | Playwright console listener | JavaScript errors during page load |
| `network_failure` | Playwright request listener | Failed network requests |
| `hidden_control` | Playwright DOM metrics | Interactive elements hidden from users |

Vision AI (via Ollama) can additionally detect:
- Overlapping text
- Low contrast
- Other visual anomalies described in screenshots

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Scan fails | Check backend logs: `http://127.0.0.1:8000/docs` |
| Q&A returns "Cannot reach Ollama" | Run `ollama serve` and ensure `qwen2.5vl:3b` is pulled |
| Vision analysis returns no findings | Ollama must be running; pull model: `ollama pull qwen2.5vl:3b` |
| Screenshots not loading | Ensure backend is running at port 8000 |
| Local test pages fail | Start the HTTP server: `.\.venv312\Scripts\python.exe -m http.server 5500` |
| CORS error in browser | Check `FRONTEND_ORIGINS` in `.env` matches your server origin |

---

## API Documentation

The FastAPI backend exposes interactive API docs at:
```
http://127.0.0.1:8000/docs
```

Key endpoints:
- `POST /api/scan` — Run a new scan (async or sync)
- `GET /api/scans` — List all scans
- `GET /api/scans/{id}` — Get scan details
- `GET /api/issues` — List all detected issues
- `GET /api/dashboard` — Dashboard metrics
- `GET /api/report/{id}` — Export scan report
- `GET /api/compare` — Compare two scans
- `POST /api/ai/analyze/{id}` — Run vision analysis
- `POST /api/ai/heal/{id}` — Run self-healing loop
- `POST /api/qa/ask` — Ask a Q&A question
- `POST /api/qa/screenshot` — Analyze uploaded screenshot
- `POST /api/rescan` — Re-scan with CSS patch injected

---

## Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
VISION_PROVIDER=ollama
VISION_MODEL=qwen2.5vl:3b
VISION_QA_MODEL=qwen2.5vl:3b
OLLAMA_HOST=http://127.0.0.1:11434
ALLOW_PUBLIC_TARGETS=true
FRONTEND_ORIGINS=http://127.0.0.1:5500,http://localhost:5500
```

To use a different vision model:
```bash
ollama pull llava:7b
VISION_MODEL=llava:7b
VISION_QA_MODEL=llava:7b
```
