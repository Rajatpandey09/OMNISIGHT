
import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omnisight_backend")

BASE_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = BASE_DIR / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

RECORDS_FILE = BASE_DIR / "scan_records.json"

# Development allowlist. Add only hostnames you trust and intend to scan.
ALLOWED_HOSTS = {"localhost", "127.0.0.1", "example.com"}

app = FastAPI(
    title="OmniSight Backend & Browser Automation",
    version="1.4.0",
    description="Browser scanning API with persistent scan history.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/artifacts",
    StaticFiles(directory=str(ARTIFACT_DIR)),
    name="artifacts",
)


class ScanRequest(BaseModel):
    url: str
    scan_id: str = Field(default_factory=lambda: f"scan-{int(datetime.now().timestamp() * 1000)}")


def load_records():
    try:
        if RECORDS_FILE.exists():
            with RECORDS_FILE.open("r", encoding="utf-8") as file:
                records = json.load(file)
                return records if isinstance(records, list) else []
    except (OSError, json.JSONDecodeError):
        logger.exception("Could not read scan history")
    return []


def save_records(records):
    temp_file = RECORDS_FILE.with_suffix(".tmp")
    with temp_file.open("w", encoding="utf-8") as file:
        json.dump(records, file, indent=2)
    temp_file.replace(RECORDS_FILE)


def validate_target(raw_url):
    try:
        parsed = urlparse(raw_url)
        hostname = (parsed.hostname or "").lower().rstrip(".")
        valid_scheme = parsed.scheme in {"http", "https"}
        valid_host = hostname in ALLOWED_HOSTS
        no_credentials = parsed.username is None and parsed.password is None

        if not valid_scheme or not valid_host or not no_credentials:
            raise ValueError
        if not parsed.netloc:
            raise ValueError

        return parsed
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail=(
                "Target URL is not permitted. Use HTTP/HTTPS and a hostname "
                "explicitly listed in ALLOWED_HOSTS in backend/main.py."
            ),
        )


def public_scan(record):
    """Return a scan record without internal filesystem paths."""
    return record


@app.get("/")
def read_root():
    return {
        "service": "OmniSight Backend & Browser Automation",
        "status": "active",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "OmniSight Backend"}


@app.get("/api/targets")
def get_targets():
    return [
        {
            "id": host,
            "name": host,
            "url": f"https://{host}" if host == "example.com" else f"http://{host}",
        }
        for host in sorted(ALLOWED_HOSTS)
    ]


@app.get("/api/scans")
def get_scans():
    return list(reversed(load_records()))


@app.get("/api/scans/{scan_id}")
def get_scan(scan_id: str):
    for record in load_records():
        if record.get("scan_id") == scan_id:
            return public_scan(record)
    raise HTTPException(status_code=404, detail="Scan not found")


@app.get("/api/issues")
def get_issues():
    # Browser metrics are not yet converted into verified issue records.
    # Return no issues rather than inventing results.
    return []


@app.get("/api/dashboard")
def get_dashboard():
    records = load_records()
    successful = [r for r in records if r.get("status") == "completed"]
    issues = []

    return {
        "total_scans": len(records),
        "issues_found": len(issues),
        "verified_resolved": 0,
        "needs_attention": 0,
        "last_updated": (
            records[-1].get("created_at") if records else None
        ),
        "recent_scans": list(reversed(records[-5:])),
        "successful_scans": len(successful),
    }


@app.post("/api/scan", status_code=status.HTTP_200_OK)
async def execute_browser_scan(payload: ScanRequest):
    validate_target(payload.url)

    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", payload.scan_id):
        raise HTTPException(status_code=400, detail="Invalid scan_id")

    records = load_records()
    if any(r.get("scan_id") == payload.scan_id for r in records):
        raise HTTPException(status_code=409, detail="scan_id already exists")

    created_at = datetime.now(timezone.utc).isoformat()
    record = {
        "scan_id": payload.scan_id,
        "id": payload.scan_id,
        "url": payload.url,
        "target": payload.url,
        "status": "running",
        "created_at": created_at,
        "results": [],
        "error": None,
    }
    records.append(record)
    save_records(records)

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                results = []

                for viewport_name, width, height in [
                    ("desktop", 1366, 768),
                    ("mobile", 390, 844),
                ]:
                    page = await browser.new_page(
                        viewport={"width": width, "height": height}
                    )
                    try:
                        await page.goto(
                            payload.url,
                            timeout=30000,
                            wait_until="domcontentloaded",
                        )
                        await page.screenshot(
                            path=str(ARTIFACT_DIR / f"{payload.scan_id}_{viewport_name}.png"),
                            full_page=True,
                        )

                        metrics = await page.evaluate("""() => {
                            const buttons = Array.from(
                                document.querySelectorAll(
                                    'button, a.btn, input[type="submit"]'
                                )
                            ).map(el => {
                                const rect = el.getBoundingClientRect();
                                return {
                                    selector: el.id ? `#${el.id}` : el.tagName.toLowerCase(),
                                    text: (el.innerText || el.value || '').trim(),
                                    x: rect.x,
                                    y: rect.y,
                                    width: rect.width,
                                    height: rect.height,
                                    is_off_screen:
                                        rect.right > window.innerWidth || rect.left < 0
                                };
                            });

                            return {
                                scroll_width: document.documentElement.scrollWidth,
                                scroll_height: document.documentElement.scrollHeight,
                                has_horizontal_overflow:
                                    document.documentElement.scrollWidth >
                                    document.documentElement.clientWidth,
                                buttons,
                                hidden_controls: Array.from(
                                    document.querySelectorAll(
                                        '[hidden], .hidden, [style*="display: none"]'
                                    )
                                ).map(el => el.id || el.className || 'unnamed_control')
                            };
                        }""")

                        results.append({
                            "viewport": viewport_name,
                            "width": width,
                            "height": height,
                            "screenshot": f"/artifacts/{payload.scan_id}_{viewport_name}.png",
                            "metrics": metrics,
                        })
                    finally:
                        await page.close()
            finally:
                await browser.close()

        record["status"] = "completed"
        record["results"] = results
        record["completed_at"] = datetime.now(timezone.utc).isoformat()

    except Exception as exc:
        logger.exception("Browser scan failed")
        record["status"] = "failed"
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["completed_at"] = datetime.now(timezone.utc).isoformat()
        save_records(records)
        raise HTTPException(
            status_code=500,
            detail=f"Browser scan failed: {type(exc).__name__}: {exc}",
        )

    save_records(records)
    return record
