# OmniSight Ollama Q&A setup

## What this adds
- `POST /api/qa/ask`: asks a question about one completed scan.
- `GET /api/qa/health`: reports the configured Ollama model.
- A responsive **Ask OmniSight** panel is loaded on the existing dashboard.
- The assistant receives only scan metadata and selected layout metrics. It does not browse arbitrary pages, apply CSS, or mark issues resolved.

## Local Windows setup
1. Install/start Ollama: https://ollama.com/download
2. In PowerShell, pull a model. The default below matches the existing local vision model:
   ```powershell
   ollama pull qwen2.5vl:3b
   ```
   You may set a separate text model if preferred:
   ```powershell
   $env:VISION_QA_MODEL="qwen2.5:3b"
   ```
3. Set the Ollama endpoint (normally the default):
   ```powershell
   $env:OLLAMA_HOST="http://127.0.0.1:11434"
   ```
4. Start the backend from the repository root:
   ```powershell
   python -m uvicorn main:app --host 127.0.0.1 --port 8000
   ```
5. Serve the repository root in another terminal:
   ```powershell
   python -m http.server 5500
   ```
6. Open `http://127.0.0.1:5500`, run a scan, wait for status `completed`, then open **Ask OmniSight** and select that scan.

## API smoke test
```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/qa/health
$body = @{ scan_id = "YOUR_COMPLETED_SCAN_ID"; question = "What issues are supported by this scan's metrics?" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/qa/ask -ContentType "application/json" -Body $body
```

## Public demo architecture
The browser frontend can be hosted publicly, but the API must run on a server that can reach Ollama. A laptop's `127.0.0.1` is not reachable from a cloud backend.
- Deploy the FastAPI service on an always-on host with Playwright/Chromium installed and persistent storage for SQLite and screenshots.
- Run Ollama on that host, or connect the backend to a securely networked Ollama server using `OLLAMA_HOST`.
- Do not expose Ollama port 11434 directly to the public internet. Put it behind private networking or an authenticated TLS gateway.
- Set `VISION_QA_MODEL` and `OLLAMA_HOST` as server environment variables.
- Set frontend `window.OmniSightAPIConfig = { baseUrl: "https://YOUR-API-HOST/api" }` before `api.js` loads. Configure the backend CORS allow-list to the exact deployed frontend origin; do not use wildcard origins for a production deployment.
- Use a persistent disk/volume for `omnisight.db` and `artifacts/`. Ephemeral function filesystems will lose scan history and screenshots.

## Important production hardening before opening public access
The current repository scanner is a prototype, not yet safe for unrestricted public URL scanning. Before public launch:
1. Replace substring-based URL checks with strict URL parsing, DNS resolution, and blocking of loopback, private, link-local, multicast, reserved and cloud-metadata IP ranges. Re-check redirects and DNS results at navigation time to prevent SSRF/DNS rebinding.
2. Run browser workers in isolated containers with CPU, memory, time, download and concurrency limits; block access to internal services and metadata endpoints at the network layer.
3. Add authentication or quotas, per-user scan ownership, request rate limits, retention controls and abuse monitoring.
4. Persist screenshots and scan data in durable storage; avoid sharing scans between anonymous users.
5. Restrict CORS to the deployed frontend origin and use HTTPS.
6. Implement actual approval and verification state transitions. Do not report a fix as applied just because an approval endpoint was called.

## Scope and current limitations
- Q&A is grounded in stored viewport metrics and scan metadata; it does not yet inspect screenshot pixels or raw page HTML.
- Chat history is not persisted between requests.
- Q&A only works after a scan has completed.
- Ollama must be reachable from the backend and the selected model must be pulled.
- This feature branch does not deploy the application or expose your laptop to the internet.
