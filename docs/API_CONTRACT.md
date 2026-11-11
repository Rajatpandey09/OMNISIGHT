# OmniSight API contract — integrated branch

Base URL for local development: `http://127.0.0.1:8000`. JSON request/response bodies use UTF-8.

| Method | Route | Purpose |
|---|---|---|
| GET | `/health` | Backend health |
| GET | `/api/targets` | Configured demo targets |
| POST | `/api/scan` | Start a scan; request includes `url`, optional `scan_id`, `viewports`, `sync` |
| GET | `/api/scans/{scan_id}` | Poll status and per-viewport screenshot/metrics/HTML |
| GET | `/api/scans` | Scan history |
| GET | `/api/issues` | Deterministic issues with screenshot and suggested CSS fields |
| POST | `/api/ai/analyze/{scan_id}` | VLM analysis using screenshot + metrics + captured body HTML |
| POST | `/api/ai/analyze/{scan_id}?screenshot_only=true` | VLM screenshot-only audit |
| POST | `/api/ai/heal/{scan_id}` | Plan → Execute → Evaluate loop in isolated Playwright context |
| POST | `/api/ai/verify/{scan_id}` | VLM + metric verification for a human-approved patch rescan |
| POST | `/api/rescan` | Apply CSS in scan browser context and compare follow-up metrics to baseline |
| POST | `/api/qa/ask` | Grounded Q&A; body: `{"scan_id":"...","question":"..."}` |
| POST | `/api/approve_fix` | Records human approval only; does not edit source files |
| POST | `/api/reject_fix` | Records human rejection |
| GET | `/api/qa/health` | Q&A provider/model status |

### VLM analysis

`POST /api/ai/analyze/{scan_id}`

Requires a completed scan with screenshot artifacts. The result includes `analyses[]` per viewport, provider outcome, findings, confidence, evidence, uncertainty and suggested fixes. `screenshot_only=true` deliberately omits DOM metrics and HTML.

### Isolated self-healing

`POST /api/ai/heal/{scan_id}`

```json
{"finding_index": 0, "viewport": "mobile", "max_attempts": 2}
```

The finding index is zero-based within that viewport's VLM findings. The endpoint generates a validated CSS proposal, applies it only to a disposable Playwright browser context, captures an after screenshot, asks the VLM to compare before/after, and combines that verdict with deterministic metrics when available. Response includes attempts, final CSS, status, `human_approval_required: true`, and `source_page_modified: false`.

### Patch rescan

`POST /api/rescan`

```json
{
  "url": "http://localhost:5500/test-pages/bug_offscreen_button.html",
  "scan_id": "original-completed-scan-id",
  "viewports": ["mobile"],
  "issue_type": "offscreen_button",
  "css_patch": "#save-profile-btn { position: static; max-width: 100%; box-sizing: border-box; }"
}
```

The original `scan_id` is required for a meaningful baseline comparison. Supported metric-specific issue types currently include `horizontal_overflow` and `offscreen_button`. Other issue types must remain inconclusive until matching deterministic verification exists.

### VLM verification after a human-approved patch

`POST /api/ai/verify/{original_scan_id}`

```json
{
  "rescan_id": "rescan-id-returned-by-api-rescan",
  "viewport": "mobile",
  "issue_type": "offscreen_button",
  "element": "#save-profile-btn"
}
```

The endpoint compares the original and follow-up screenshots with the configured vision provider and combines that result with available deterministic metrics. It returns `verified_resolved` only when both signals support the fix. If a metric is unavailable, the result remains inconclusive rather than accepting a model-only success claim.
