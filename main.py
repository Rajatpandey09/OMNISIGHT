import os
import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import re
import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlparse, quote

# Load .env before any other module reads env vars (safe no-op when not installed)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Depends, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import init_db, get_db, SessionLocal, ScanRecord
from vision_api import router as vision_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omnisight_backend")

# Initialize SQLite database schema
init_db()

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app_instance):
    """
    On startup: find any completed scan whose screenshot files are missing from
    disk and queue them for re-capture in the background. This keeps the DB
    and artifact directory in sync after restarts or artifact cleans.
    """
    db: Session = SessionLocal()
    try:
        records = db.query(ScanRecord).filter(ScanRecord.status == "completed").all()
        stale = []
        for record in records:
            shots = [
                os.path.join(ARTIFACT_DIR, Path(res.get("screenshot", "")).name)
                for res in (record.results or [])
                if res.get("screenshot")
            ]
            if shots and any(not os.path.isfile(s) for s in shots):
                stale.append(record)
        if stale:
            logger.info(f"Startup: {len(stale)} scan(s) have missing artifacts — queuing re-capture.")
        for record in stale:
            viewports = list({
                res.get("viewport") for res in (record.results or [])
                if res.get("viewport")
            }) or ["desktop", "mobile"]
            record.status = "pending"
            record.results = []
            record.error = None
            db.commit()
            asyncio.create_task(run_scan_worker(record.scan_id, record.url, viewports))
    except Exception as exc:
        logger.warning(f"Startup artifact check failed: {exc}")
    finally:
        db.close()
    yield  # app runs here

app = FastAPI(
    title="OmniSight Backend & Browser Automation",
    version="1.7.0",
    description="Production-grade backend service for multimodal UI self-healing, SQLite persistence, and asynchronous browser automation with resilient retries.",
    contact={
        "name": "Priyanshu",
        "role": "Backend & Browser Automation Engineer"
    },
    lifespan=lifespan
)

# Configure exact browser origins; never use wildcard CORS for a public deployment.
_default_origins = "http://127.0.0.1:5500,http://localhost:5500,http://127.0.0.1:8000,http://localhost:8000"
FRONTEND_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("FRONTEND_ORIGINS", _default_origins).split(",")
    if origin.strip()
]
# Allow null origin for file:// access during local development
if os.getenv("ALLOW_FILE_ORIGIN", "true").lower() == "true":
    FRONTEND_ORIGINS = ["null"] + FRONTEND_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

ARTIFACT_DIR = "artifacts"
os.makedirs(ARTIFACT_DIR, exist_ok=True)

# Mount artifacts directory for direct screenshot access by frontend and visual review
app.mount("/artifacts", StaticFiles(directory=ARTIFACT_DIR), name="artifacts")

# Register sub-routers
app.include_router(vision_router)

# Local test pages are explicitly allowed. Public hosts are accepted only after
# DNS/IP checks, and every browser subrequest is checked again to reduce SSRF risk.
ALLOWED_DOMAINS = {"localhost", "127.0.0.1", "example.com"}
LOCAL_PORTS = {5500, 8000}

def _host_resolves_publicly(host: str) -> bool:
    try:
        literal = ipaddress.ip_address(host)
        return literal.is_global
    except ValueError:
        pass
    try:
        answers = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        addresses = {ipaddress.ip_address(item[4][0]) for item in answers}
        return bool(addresses) and all(address.is_global for address in addresses)
    except (OSError, ValueError):
        return False

def validate_target_url(url: str):
    """Allow local demo hosts or publicly routable HTTP(S) websites only."""
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError:
        raise HTTPException(status_code=400, detail="Enter a valid website URL.")
    local_demo = host in ALLOWED_DOMAINS and (port is None or port in LOCAL_PORTS or port in {80, 443})
    public_site = (
        os.getenv("ALLOW_PUBLIC_TARGETS", "true").lower() == "true"
        and bool(host) and "." in host and host not in {"localhost"}
        and port in (None, 80, 443) and _host_resolves_publicly(host)
    )
    if (parsed.scheme not in {"http", "https"} or not parsed.netloc
            or parsed.username is not None or parsed.password is not None
            or not (local_demo or public_site)):
        raise HTTPException(status_code=400, detail="Target must be a public HTTP/HTTPS website, or one of the configured local demo pages.")


class ScanRequest(BaseModel):
    url: str
    scan_id: Optional[str] = None
    viewports: Optional[List[str]] = ["desktop", "mobile"]
    sync: Optional[bool] = False


class RescanRequest(BaseModel):
    url: str
    css_patch: str
    scan_id: Optional[str] = None
    viewports: Optional[List[str]] = ["desktop", "mobile"]
    issue_type: Optional[str] = None


class VerifyFixRequest(BaseModel):
    issue_id: Optional[str] = None
    scan_id: Optional[str] = None
    url: Optional[str] = None
    css_patch: Optional[str] = None


class FixActionRequest(BaseModel):
    issue_id: Optional[str] = None
    scan_id: Optional[str] = None


async def navigate_with_retry(page, url: str, retries: int = 3, delay: int = 2):
    """Kept for backward compatibility with /api/rescan async path."""
    for attempt in range(retries):
        try:
            await page.goto(url, timeout=30000, wait_until="networkidle")
            return
        except Exception as e:
            if attempt == retries - 1:
                raise e
            logger.warning(f"Navigation attempt {attempt + 1} failed for {url}: {str(e)}. Retrying...")
            await asyncio.sleep(delay * (attempt + 1))


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = asyncio.get_event_loop().time()
    
    response = await call_next(request)
    
    process_time = asyncio.get_event_loop().time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Request-ID"] = request_id
    
    logger.info(f"ReqID: {request_id} | Path: {request.url.path} | Method: {request.method} | Duration: {process_time:.4f}s | Status: {response.status_code}")
    return response


def _run_playwright_scan_sync(scan_id: str, url: str, viewports: List[str], css_patch: Optional[str] = None) -> List[dict]:
    """
    Synchronous Playwright scan that runs inside a thread pool executor.
    This avoids the Windows asyncio ProactorEventLoop restriction when
    launching subprocesses from an already-running event loop.
    """
    from playwright.sync_api import sync_playwright
    import logging as _logging
    _logger = _logging.getLogger("omnisight_playwright")

    viewport_configs = {
        "desktop": {"width": 1366, "height": 768},
        "mobile": {"width": 390, "height": 844}
    }

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for vp in viewports:
                cfg = viewport_configs.get(vp, {"width": 1366, "height": 768})
                context = browser.new_context(
                    viewport={"width": cfg["width"], "height": cfg["height"]}
                )
                page = context.new_page()
                console_errors = []
                network_failures = []

                page.on("console", lambda msg: console_errors.append(
                    {"level": msg.type, "text": msg.text}
                ) if msg.type in ("error", "warning") else None)

                page.on("requestfailed", lambda req: network_failures.append(
                    {"url": req.url, "failure": req.failure}
                ))

                try:
                    # Navigate with retry
                    for attempt in range(3):
                        try:
                            page.goto(url, timeout=30000, wait_until="domcontentloaded")
                            break
                        except Exception as nav_e:
                            if attempt == 2:
                                raise nav_e
                            import time
                            time.sleep(2 * (attempt + 1))

                    if css_patch:
                        _logger.info(f"Injecting CSS patch into page for viewport {vp}")
                        page.add_style_tag(content=css_patch)
                        page.wait_for_timeout(300)

                    screenshot_filename = f"{scan_id}_{vp}.png"
                    screenshot_path = os.path.join(ARTIFACT_DIR, screenshot_filename)
                    page.screenshot(path=screenshot_path, full_page=True)

                    try:
                        relevant_html = page.locator("body").inner_html()[:12000]
                    except Exception:
                        relevant_html = ""

                    metrics = page.evaluate("""() => {
                        const buttons = Array.from(document.querySelectorAll('button, a.btn, input[type="submit"]')).map(el => {
                            const rect = el.getBoundingClientRect();
                            return {
                                selector: el.id ? '#' + el.id : (el.className ? '.' + el.className.split(' ')[0] : el.tagName.toLowerCase()),
                                text: (el.innerText || el.value || '').trim(),
                                x: rect.x, y: rect.y, width: rect.width, height: rect.height,
                                is_off_screen: rect.right > window.innerWidth || rect.left < 0
                            };
                        });
                        const hiddenElements = Array.from(document.querySelectorAll('[hidden], .hidden, [style*="display: none"]'))
                            .map(el => el.id || el.className || 'unnamed_control');
                        const images = Array.from(document.querySelectorAll('img')).map(img => ({
                            src: img.src,
                            naturalWidth: img.naturalWidth,
                            naturalHeight: img.naturalHeight,
                            is_broken: img.naturalWidth === 0 && img.complete
                        }));
                        return {
                            scroll_width: document.documentElement.scrollWidth,
                            scroll_height: document.documentElement.scrollHeight,
                            has_horizontal_overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
                            buttons: buttons,
                            hidden_controls: hiddenElements,
                            images: images,
                            broken_images: images.filter(img => img.is_broken).map(img => img.src),
                            page_title: document.title || '',
                            meta_description: (document.querySelector('meta[name="description"]') || {}).content || '',
                            h1_count: document.querySelectorAll('h1').length,
                            link_count: document.querySelectorAll('a[href]').length,
                            form_count: document.querySelectorAll('form').length
                        };
                    }""")

                    results.append({
                        "viewport": vp,
                        "width": cfg["width"],
                        "height": cfg["height"],
                        "screenshot": screenshot_filename,
                        "metrics": metrics,
                        "relevant_html": relevant_html,
                        "console_errors": console_errors[:50],
                        "network_failures": network_failures[:20],
                    })
                    _logger.info(f"Captured {vp} viewport for scan '{scan_id}'")
                finally:
                    page.close()
                    context.close()
        finally:
            browser.close()

    return results


async def run_scan_worker(scan_id: str, url: str, viewports: List[str], css_patch: Optional[str] = None):
    """
    Background worker that runs Playwright in a thread pool (required on Windows
    where asyncio's default event loop doesn't support subprocess creation from
    within an already-running loop).
    """
    logger.info(f"Starting browser automation for scan '{scan_id}' on {url}")
    db: Session = SessionLocal()

    try:
        record = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_id).first()
        if not record:
            logger.error(f"Scan record '{scan_id}' not found in database.")
            return
        record.status = "processing"
        db.commit()

        # Run synchronous Playwright in a thread pool to avoid event loop issues on Windows
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            _run_playwright_scan_sync, scan_id, url, viewports, css_patch
        )

        db.expire_all()
        record = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_id).first()
        if record:
            record.status = "completed"
            record.results = results
            record.error = None
            record.completed_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Scan '{scan_id}' completed with {len(results)} viewport captures.")

    except Exception as e:
        logger.exception(f"Automation execution failed for scan '{scan_id}': {e}")
        try:
            db.expire_all()
            record = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_id).first()
            if record:
                record.status = "failed"
                record.error = f"{type(e).__name__}: {str(e)}"
                record.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            logger.exception("Could not update scan record after failure")
    finally:
        db.close()


def _lookup_scan(db: Session, scan_id: str) -> ScanRecord | None:
    """Resolve a scan by string scan_id OR by numeric integer id.
    
    The frontend sometimes passes the SQLite auto-increment id (e.g. '23')
    instead of the string scan_id (e.g. 'scan-abc123'). This helper handles both.
    """
    record = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_id).first()
    if not record and scan_id.isdigit():
        record = db.query(ScanRecord).filter(ScanRecord.id == int(scan_id)).first()
    return record


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Suppress browser 404 for favicon."""
    from fastapi.responses import Response
    # Minimal 1x1 transparent ICO
    ico = bytes([
        0,0,1,0,1,0,1,1,0,0,1,0,32,0,
        40,0,0,0,16,0,0,0,40,0,0,0,1,0,0,0,2,0,0,0,1,0,32,0,
        0,0,0,0,4,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,0,
    ])
    return Response(content=ico, media_type="image/x-icon")


@app.get("/", status_code=status.HTTP_200_OK, tags=["System"])
def read_root():
    return {
        "service": "OmniSight Backend & Browser Automation",
        "status": "active",
        "docs": "/docs",
        "role": "Member 2 - Backend & Browser Automation"
    }


@app.get("/health", status_code=status.HTTP_200_OK, tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": "OmniSight Backend"
    }


@app.post("/api/scan", tags=["Automation"])
async def create_scan(
    payload: ScanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Initiate a browser layout scan.
    By default runs asynchronously via FastAPI BackgroundTasks and returns 202 Accepted.
    If sync=True, waits for execution and returns 200 OK.
    """
    validate_target_url(payload.url)

    scan_identifier = payload.scan_id or f"scan-{uuid.uuid4().hex[:8]}"
    viewports = payload.viewports or ["desktop", "mobile"]

    # Check for existing scan ID or create new record
    existing = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_identifier).first()
    if existing:
        scan_record = existing
        scan_record.status = "pending"
        scan_record.url = payload.url
        scan_record.viewports = viewports
        scan_record.results = []
        scan_record.error = None
        scan_record.created_at = datetime.now(timezone.utc)
        scan_record.completed_at = None
    else:
        scan_record = ScanRecord(
            scan_id=scan_identifier,
            url=payload.url,
            status="pending",
            viewports=viewports,
            results=[]
        )
        db.add(scan_record)

    db.commit()
    db.refresh(scan_record)

    # Synchronous execution mode (for testing or immediate evaluation)
    if payload.sync:
        await run_scan_worker(scan_identifier, payload.url, viewports)
        # Re-query from a fresh read to get the committed result from the worker
        db.expire_all()
        db.refresh(scan_record)
        return scan_record.to_dict()

    # Asynchronous background execution (default for production)
    background_tasks.add_task(run_scan_worker, scan_identifier, payload.url, viewports, None)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "scan_id": scan_identifier,
            "status": "pending",
            "url": payload.url,
            "viewports": viewports,
            "message": "Scan scheduled in background. Poll /api/scans/{scan_id} for progress.",
            "created_at": scan_record.created_at.isoformat() if scan_record.created_at else None,
            "results": []
        }
    )


@app.get("/api/scans/{scan_id}", status_code=status.HTTP_200_OK, tags=["Scans"])
def get_scan_status(scan_id: str, db: Session = Depends(get_db)):
    """Retrieve current status, metadata, and results for a specific scan."""
    record = _lookup_scan(db, scan_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan '{scan_id}' not found."
        )
    return record.to_dict()


@app.get("/api/scans", status_code=status.HTTP_200_OK, tags=["Scans"])
def get_scan_history(db: Session = Depends(get_db)):
    """Retrieve history of all executed browser scans from persistent storage."""
    records = db.query(ScanRecord).order_by(ScanRecord.id.desc()).all()
    scans_list = [r.to_dict() for r in records]
    return {
        "scans": scans_list,
        "items": scans_list,
        "total": len(scans_list)
    }


@app.delete("/api/scans/{scan_id}", status_code=status.HTTP_200_OK, tags=["Scans"])
def delete_scan(scan_id: str, db: Session = Depends(get_db)):
    """Delete a scan record from the database and remove associated screenshot artifacts."""
    record = _lookup_scan(db, scan_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan '{scan_id}' not found."
        )

    # Clean up associated artifacts
    for vp in (record.viewports or ["desktop", "mobile"]):
        screenshot_file = os.path.join(ARTIFACT_DIR, f"{scan_id}_{vp}.png")
        if os.path.exists(screenshot_file):
            try:
                os.remove(screenshot_file)
            except OSError:
                pass

    db.delete(record)
    db.commit()
    return {"message": f"Scan '{scan_id}' deleted successfully."}


@app.post("/api/rescan", status_code=status.HTTP_200_OK, tags=["Self-Healing"])
async def rescan_with_patch(payload: RescanRequest, db: Session = Depends(get_db)):
    """
    Self-healing verification endpoint:
    Applies a proposed CSS patch directly into the page and rescans to verify defect resolution.
    """
    validate_target_url(payload.url)
    if len(payload.css_patch) > 4000 or re.search(r"url\s*\(|@import|expression\s*\(|javascript:", payload.css_patch, re.I):
        raise HTTPException(status_code=400, detail="CSS patch contains unsupported or unsafe content.")

    rescan_id = f"rescan-{uuid.uuid4().hex[:8]}"
    viewports = payload.viewports or ["desktop", "mobile"]

    # Create the persistent record BEFORE invoking the worker. The worker
    # updates an existing ScanRecord; without this row it silently produces
    # no results, which previously caused an empty scan to be marked resolved.
    rescan_record = ScanRecord(
        scan_id=rescan_id,
        url=payload.url,
        status="pending",
        viewports=viewports,
        results=[]
    )
    db.add(rescan_record)
    db.commit()
    db.refresh(rescan_record)

    await run_scan_worker(rescan_id, payload.url, viewports, css_patch=payload.css_patch)

    db.expire_all()
    record = db.query(ScanRecord).filter(ScanRecord.scan_id == rescan_id).first()
    scan_data = record.to_dict() if record else {"results": []}
    results = scan_data.get("results") or []

    # Never treat an empty, failed, or partial scan as evidence of a fix.
    complete_capture = (
        record is not None
        and record.status == "completed"
        and len(results) == len(viewports)
        and all(isinstance(item, dict) and isinstance(item.get("metrics"), dict) for item in results)
    )
    baseline = db.query(ScanRecord).filter(ScanRecord.scan_id == payload.scan_id).first() if payload.scan_id else None
    baseline_results = (baseline.results or []) if baseline and baseline.status == "completed" else []
    baseline_has_overflow = any(
        item.get("metrics", {}).get("has_horizontal_overflow") is True
        for item in baseline_results
    )
    baseline_has_offscreen = any(
        button.get("is_off_screen") is True
        for item in baseline_results
        for button in item.get("metrics", {}).get("buttons", [])
    )
    remaining_overflow = any(
        item.get("metrics", {}).get("has_horizontal_overflow") is True for item in results
    )
    remaining_offscreen = any(
        button.get("is_off_screen") is True
        for item in results for button in item.get("metrics", {}).get("buttons", [])
    )
    checks = []
    baseline_matches_issue = True
    if payload.issue_type == "horizontal_overflow":
        baseline_matches_issue = baseline_has_overflow
    elif payload.issue_type == "offscreen_button":
        baseline_matches_issue = baseline_has_offscreen
    elif payload.issue_type:
        baseline_matches_issue = False
    if baseline_has_overflow:
        checks.append(not remaining_overflow)
    if baseline_has_offscreen:
        checks.append(not remaining_offscreen)
    # Only mark inconclusive from here if no deterministic checks exist at all.
    # Do NOT reset baseline_matches_issue — it was already set correctly above.
    if not complete_capture or not baseline_results or not baseline_matches_issue or not checks:
        verification_state = "inconclusive"
    else:
        verification_state = "verified_resolved" if all(checks) else "verification_failed"

    # Persist the verification outcome to the original scan record so the
    # dashboard and issue list survive a page refresh / server restart.
    if baseline and verification_state == "verified_resolved":
        baseline.status = "verified_resolved"
        baseline.completed_at = datetime.now(timezone.utc)
        db.commit()

    return {
        "rescan_id": rescan_id,
        "verification_state": verification_state,
        "scan_status": record.status if record else "missing",
        "captured_viewports": len(results),
        "expected_viewports": len(viewports),
        "css_patch_applied": payload.css_patch,
        "url": payload.url,
        "scan_data": scan_data,
        "message": (
            "Patch verification completed against captured viewport metrics."
            if verification_state == "verified_resolved"
            else "Verification was not successful. Inspect scan_status, captured_viewports, and scan_data before making a resolution claim."
        )
    }


@app.post("/api/verify_fix", status_code=status.HTTP_200_OK, tags=["Self-Healing"])
async def verify_fix_endpoint(payload: VerifyFixRequest, db: Session = Depends(get_db)):
    """
    Endpoint matching the frontend client contract (src/lib/api.js `verifyFix(id)`).
    Verifies whether a proposed fix resolves the identified UI issue.
    """
    target_scan_id = payload.scan_id or payload.issue_id
    if not target_scan_id:
        return {
            "status": "inconclusive",
            "message": "Neither scan_id nor issue_id was provided for verification."
        }

    record = db.query(ScanRecord).filter(ScanRecord.scan_id == target_scan_id).first()
    target_url = payload.url or (record.url if record else "http://localhost:8000")

    if payload.css_patch:
        rescan_req = RescanRequest(url=target_url, css_patch=payload.css_patch, scan_id=target_scan_id)
        return await rescan_with_patch(rescan_req, db)

    return {
        "status": "inconclusive" if record and record.status == "completed" else "pending",
        "scan_id": target_scan_id,
        "message": (
            "A completed baseline scan is not proof that a fix worked. Submit the approved CSS patch to /api/rescan with the original scan_id to run a follow-up verification."
            if record and record.status == "completed"
            else "The original scan is not yet complete; verification cannot run."
        )
    }


class VerifyStateRequest(BaseModel):
    verification_state: str  # "verified_resolved" | "verification_failed" | "inconclusive"
    css_patch: Optional[str] = None
    rescan_id: Optional[str] = None


@app.patch("/api/scans/{scan_id}/verify", status_code=status.HTTP_200_OK, tags=["Self-Healing"])
def persist_verification_state(scan_id: str, payload: VerifyStateRequest, db: Session = Depends(get_db)):
    """
    Persist the verification outcome on the original scan record so the state
    survives page refreshes and server restarts.
    Called by the frontend after a successful /api/ai/verify response.
    """
    allowed = {"verified_resolved", "verification_failed", "inconclusive"}
    if payload.verification_state not in allowed:
        raise HTTPException(status_code=400, detail=f"verification_state must be one of {allowed}")
    record = _lookup_scan(db, scan_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id}' not found.")
    record.status = payload.verification_state
    record.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "scan_id": scan_id,
        "status": record.status,
        "message": f"Scan '{scan_id}' marked as {payload.verification_state}."
    }


@app.get("/api/targets", status_code=status.HTTP_200_OK, tags=["Frontend"])
def get_targets():
    """Return available targets for the frontend scan target selector. Users may also enter any public URL directly."""
    return [
        {"id": "custom", "name": "— Enter your own URL below —", "url": ""},
        {"id": "example-com", "name": "Example.com (External Demo)", "url": "https://example.com"},
        {"id": "localhost-testbed", "name": "Local Testbed Suite (Port 5500)", "url": "http://localhost:5500/test-pages/index.html"},
        {"id": "bug-overflow", "name": "Bug: Horizontal Overflow", "url": "http://localhost:5500/test-pages/bug_overflow.html"},
        {"id": "bug-offscreen", "name": "Bug: Off-Screen Button", "url": "http://localhost:5500/test-pages/bug_offscreen_button.html"},
        {"id": "bug-overlap", "name": "Bug: Overlapping Text", "url": "http://localhost:5500/test-pages/bug_overlapping_text.html"},
        {"id": "bug-hidden", "name": "Bug: Hidden Interactive Control", "url": "http://localhost:5500/test-pages/bug_hidden_control.html"},
        {"id": "bug-contrast", "name": "Bug: Low Contrast", "url": "http://localhost:5500/test-pages/bug_contrast.html"},
        {"id": "clean-page", "name": "Clean Reference Page (No Bugs)", "url": "http://localhost:5500/test-pages/clean.html"},
    ]


@app.get("/api/dashboard", status_code=status.HTTP_200_OK, tags=["Frontend"])
def get_dashboard(db: Session = Depends(get_db)):
    """Aggregate metric cards for the React QA dashboard."""
    records = db.query(ScanRecord).all()
    total_scans = len(records)

    all_issues = []
    verified_count = 0
    for r in records:
        scan_dict = r.to_dict()
        for res in scan_dict.get("results", []):
            metrics = res.get("metrics", {})
            if metrics.get("has_horizontal_overflow"):
                all_issues.append({"scan_id": r.scan_id, "type": "horizontal_overflow"})
            for b in metrics.get("buttons", []):
                if b.get("is_off_screen"):
                    all_issues.append({"scan_id": r.scan_id, "type": "offscreen_button"})
        if r.status == "verified_resolved":
            verified_count += 1

    issues_found = len(all_issues)
    needs_attention = max(0, issues_found - verified_count)

    return {
        "total_scans": total_scans,
        "issues_found": issues_found,
        "verified_resolved": verified_count,
        "needs_attention": needs_attention,
        "last_updated": datetime.now(timezone.utc).isoformat() if records else None
    }


@app.get("/api/issues", status_code=status.HTTP_200_OK, tags=["Frontend"])
def get_issues(request: Request, db: Session = Depends(get_db)):
    """Return detected issues with frontend-compatible screenshot and CSS fields."""
    records = db.query(ScanRecord).all()
    issues_list = []
    for r in records:
        # If this scan was verified, all its issues should reflect that
        scan_verified = r.status == "verified_resolved"
        issue_state = "verified" if scan_verified else "detected"
        issue_verification_state = "verified_resolved" if scan_verified else "detected"
        for res in (r.results or []):
            vp = res.get("viewport", "desktop")
            metrics = res.get("metrics", {})
            screenshot = res.get("screenshot", "")
            console_errors = res.get("console_errors", [])
            network_failures = res.get("network_failures", [])
            screenshot_url = (
                f"{str(request.base_url).rstrip('/')}/artifacts/{quote(Path(screenshot).name)}"
                if screenshot and (Path(ARTIFACT_DIR) / Path(screenshot).name).is_file()
                else None
            )

            # Horizontal overflow
            has_offscreen_control = any(
                button.get("is_off_screen")
                for button in metrics.get("buttons", [])
            )
            if metrics.get("has_horizontal_overflow") and not has_offscreen_control:
                overflow_css = (
                    "/* Scope this to the element causing overflow after inspecting the page. */\n"
                    "html, body { max-width: 100%; overflow-x: clip; }\n"
                    "/* Prefer fixing the oversized child: */\n"
                    ".wide-banner, .wide-content { max-width: 100%; box-sizing: border-box; }"
                )
                issue_identifier = f"ISSUE-{r.scan_id}-{vp}-OVERFLOW"
                issues_list.append({
                    "id": issue_identifier,
                    "issue_id": issue_identifier,
                    "title": f"Horizontal Overflow Detected ({vp.capitalize()})",
                    "category": "responsive_layout",
                    "type": "horizontal_overflow",
                    "issue_type": "horizontal_overflow",
                    "viewport": vp,
                    "severity": "high" if vp == "mobile" else "medium",
                    "state": issue_state,
                    "verification_state": issue_verification_state,
                    "status": issue_state,
                    "scan_id": r.scan_id,
                    "target_url": r.url,
                    "screenshot": screenshot_url,
                    "screenshot_url": screenshot_url,
                    "before_screenshot": screenshot_url,
                    "suggested_fix": overflow_css,
                    "suggested_css": overflow_css,
                    "description": f"Content scroll width ({metrics.get('scroll_width')}px) exceeds visible screen width ({res.get('width')}px).",
                    "source": "playwright_metrics"
                })

            # Off-screen buttons
            for idx, b in enumerate(metrics.get("buttons", [])):
                if b.get("is_off_screen"):
                    button_css = (
                        f"{b.get('selector') or 'button'} {{ "
                        "position: static; max-width: 100%; box-sizing: border-box; "
                        "margin-inline: auto; }"
                    )
                    issue_identifier = f"ISSUE-{r.scan_id}-{vp}-BUTTON-{idx}"
                    issues_list.append({
                        "id": issue_identifier,
                        "issue_id": issue_identifier,
                        "title": f"Off-Screen Button ({b.get('text') or b.get('selector')})",
                        "category": "responsive_layout",
                        "type": "offscreen_button",
                        "issue_type": "offscreen_button",
                        "viewport": vp,
                        "severity": "high",
                        "state": issue_state,
                        "verification_state": issue_verification_state,
                        "status": issue_state,
                        "scan_id": r.scan_id,
                        "target_url": r.url,
                        "screenshot": screenshot_url,
                        "screenshot_url": screenshot_url,
                        "before_screenshot": screenshot_url,
                        "suggested_fix": button_css,
                        "suggested_css": button_css,
                        "description": "Target interactive button is clipped outside the visible viewport boundary. This element also contributes to the page's horizontal overflow.",
                        "source": "playwright_metrics"
                    })

            # Broken images
            for broken_src in metrics.get("broken_images", [])[:5]:
                issue_identifier = f"ISSUE-{r.scan_id}-{vp}-BROKEN-IMG-{abs(hash(broken_src)) % 9999}"
                issues_list.append({
                    "id": issue_identifier,
                    "issue_id": issue_identifier,
                    "title": f"Broken Image ({broken_src[:60]}…)" if len(broken_src) > 60 else f"Broken Image",
                    "category": "broken_images",
                    "type": "broken_image",
                    "issue_type": "broken_image",
                    "viewport": vp,
                    "severity": "medium",
                    "state": issue_state,
                    "verification_state": issue_verification_state,
                    "status": issue_state,
                    "scan_id": r.scan_id,
                    "target_url": r.url,
                    "screenshot": screenshot_url,
                    "screenshot_url": screenshot_url,
                    "before_screenshot": screenshot_url,
                    "suggested_fix": f"/* Verify the image source URL is correct */\n/* Broken: {broken_src[:100]} */",
                    "suggested_css": "",
                    "description": f"An image with zero natural dimensions was detected. Source: {broken_src[:200]}",
                    "source": "playwright_metrics"
                })

            # Console errors
            js_errors = [e for e in console_errors if e.get("level") == "error"]
            if js_errors:
                error_text = "; ".join(e.get("text", "")[:100] for e in js_errors[:3])
                issue_identifier = f"ISSUE-{r.scan_id}-{vp}-CONSOLE-ERRORS"
                issues_list.append({
                    "id": issue_identifier,
                    "issue_id": issue_identifier,
                    "title": f"Console Errors Detected ({len(js_errors)} error{'s' if len(js_errors) != 1 else ''})",
                    "category": "console_errors",
                    "type": "console_error",
                    "issue_type": "console_error",
                    "viewport": vp,
                    "severity": "medium",
                    "state": issue_state,
                    "verification_state": issue_verification_state,
                    "status": issue_state,
                    "scan_id": r.scan_id,
                    "target_url": r.url,
                    "screenshot": screenshot_url,
                    "screenshot_url": screenshot_url,
                    "before_screenshot": screenshot_url,
                    "suggested_fix": "",
                    "suggested_css": "",
                    "description": f"JavaScript console errors: {error_text}",
                    "source": "playwright_console"
                })

            # Failed network requests
            if network_failures:
                fail_text = "; ".join(nf.get("url", "")[:80] for nf in network_failures[:3])
                issue_identifier = f"ISSUE-{r.scan_id}-{vp}-NETWORK-FAILS"
                issues_list.append({
                    "id": issue_identifier,
                    "issue_id": issue_identifier,
                    "title": f"Failed Network Requests ({len(network_failures)} failed)",
                    "category": "network_failures",
                    "type": "network_failure",
                    "issue_type": "network_failure",
                    "viewport": vp,
                    "severity": "medium",
                    "state": issue_state,
                    "verification_state": issue_verification_state,
                    "status": issue_state,
                    "scan_id": r.scan_id,
                    "target_url": r.url,
                    "screenshot": screenshot_url,
                    "screenshot_url": screenshot_url,
                    "before_screenshot": screenshot_url,
                    "suggested_fix": "",
                    "suggested_css": "",
                    "description": f"Network requests failed: {fail_text}",
                    "source": "playwright_network"
                })

            # Hidden interactive controls
            hidden = metrics.get("hidden_controls", [])
            if hidden:
                issue_identifier = f"ISSUE-{r.scan_id}-{vp}-HIDDEN-CONTROLS"
                issues_list.append({
                    "id": issue_identifier,
                    "issue_id": issue_identifier,
                    "title": f"Hidden Interactive Controls ({len(hidden)} found)",
                    "category": "accessibility",
                    "type": "hidden_control",
                    "issue_type": "hidden_control",
                    "viewport": vp,
                    "severity": "low",
                    "state": issue_state,
                    "verification_state": issue_verification_state,
                    "status": issue_state,
                    "scan_id": r.scan_id,
                    "target_url": r.url,
                    "screenshot": screenshot_url,
                    "screenshot_url": screenshot_url,
                    "before_screenshot": screenshot_url,
                    "suggested_fix": "",
                    "suggested_css": "",
                    "description": f"Interactive elements with display:none, hidden attribute, or zero dimensions: {', '.join(str(h) for h in hidden[:5])}",
                    "source": "playwright_metrics"
                })

    return issues_list


@app.post("/api/approve_fix", status_code=status.HTTP_200_OK, tags=["Frontend"])
def approve_fix(payload: FixActionRequest):
    """Acknowledge reviewer approval without falsely claiming the patch was applied."""
    return {
        "status": "approved",
        "applied": False,
        "message": (
            f"Proposal for '{payload.issue_id or payload.scan_id}' was approved by the reviewer. "
            "No target-site files were changed by this endpoint; run an isolated patch and "
            "follow-up verification before marking the issue resolved."
        )
    }


@app.post("/api/reject_fix", status_code=status.HTTP_200_OK, tags=["Frontend"])
def reject_fix(payload: FixActionRequest):
    """Record human rejection of a proposed fix."""
    return {
        "status": "rejected",
        "message": f"Fix for issue '{payload.issue_id or payload.scan_id}' has been rejected."
    }


@app.get("/api/artifacts", status_code=status.HTTP_200_OK, tags=["Artifacts"])
def list_artifacts():
    """List all generated screenshot artifacts and their file sizes."""
    if not os.path.exists(ARTIFACT_DIR):
        return {"artifacts": [], "total_files": 0}
    
    files = []
    for filename in os.listdir(ARTIFACT_DIR):
        file_path = os.path.join(ARTIFACT_DIR, filename)
        if os.path.isfile(file_path):
            files.append({
                "filename": filename,
                "size_bytes": os.path.getsize(file_path)
            })
    return {"artifacts": files, "total_files": len(files)}


@app.delete("/api/artifacts/clean", status_code=status.HTTP_200_OK, tags=["Artifacts"])
def clean_artifacts():
    """Delete all stored screenshot artifacts to free up local disk space."""
    if not os.path.exists(ARTIFACT_DIR):
        return {"message": "Artifact directory does not exist."}
    
    deleted_count = 0
    for filename in os.listdir(ARTIFACT_DIR):
        file_path = os.path.join(ARTIFACT_DIR, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
            deleted_count += 1
            
    return {"message": f"Successfully deleted {deleted_count} artifact file(s)."}


@app.get("/api/compare", status_code=status.HTTP_200_OK, tags=["Scans"])
def compare_scans(scan_id_a: str, scan_id_b: str, db: Session = Depends(get_db)):
    """
    Compare two completed scans and return a diff of detected issues,
    identifying new issues, resolved issues, and recurring issues.
    """
    record_a = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_id_a).first()
    record_b = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_id_b).first()

    if not record_a:
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id_a}' not found.")
    if not record_b:
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id_b}' not found.")

    def extract_issue_signatures(record):
        sigs = set()
        for res in (record.results or []):
            vp = res.get("viewport", "desktop")
            metrics = res.get("metrics", {})
            if metrics.get("has_horizontal_overflow"):
                sigs.add(f"{vp}:horizontal_overflow")
            for b in metrics.get("buttons", []):
                if b.get("is_off_screen"):
                    sigs.add(f"{vp}:offscreen_button:{b.get('selector','?')}")
            for broken in metrics.get("broken_images", []):
                sigs.add(f"{vp}:broken_image:{broken[:60]}")
            console_errs = res.get("console_errors", [])
            if any(e.get("level") == "error" for e in console_errs):
                sigs.add(f"{vp}:console_errors")
            if res.get("network_failures"):
                sigs.add(f"{vp}:network_failures")
        return sigs

    sigs_a = extract_issue_signatures(record_a)
    sigs_b = extract_issue_signatures(record_b)

    new_issues = sorted(sigs_b - sigs_a)
    resolved_issues = sorted(sigs_a - sigs_b)
    recurring_issues = sorted(sigs_a & sigs_b)

    def describe(sig):
        parts = sig.split(":", 2)
        vp = parts[0] if parts else "unknown"
        kind = parts[1] if len(parts) > 1 else "unknown"
        detail = parts[2] if len(parts) > 2 else ""
        return {"viewport": vp, "type": kind, "detail": detail, "signature": sig}

    return {
        "scan_a": {
            "scan_id": record_a.scan_id,
            "url": record_a.url,
            "status": record_a.status,
            "created_at": record_a.created_at.isoformat() if record_a.created_at else None,
            "issue_count": len(sigs_a),
        },
        "scan_b": {
            "scan_id": record_b.scan_id,
            "url": record_b.url,
            "status": record_b.status,
            "created_at": record_b.created_at.isoformat() if record_b.created_at else None,
            "issue_count": len(sigs_b),
        },
        "new_issues": [describe(s) for s in new_issues],
        "resolved_issues": [describe(s) for s in resolved_issues],
        "recurring_issues": [describe(s) for s in recurring_issues],
        "summary": {
            "new": len(new_issues),
            "resolved": len(resolved_issues),
            "recurring": len(recurring_issues),
        }
    }


@app.get("/api/report/{scan_id}", status_code=status.HTTP_200_OK, tags=["Reports"])
def export_scan_report(scan_id: str, request: Request, db: Session = Depends(get_db)):
    """
    Export a full scan report as a structured JSON document suitable for download.
    Includes scan metadata, all viewport captures, detected issues, and screenshots.
    """
    record = _lookup_scan(db, scan_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id}' not found.")

    base_url = str(request.base_url).rstrip("/")
    results_with_urls = []
    for res in (record.results or []):
        shot = res.get("screenshot", "")
        shot_url = (
            f"{base_url}/artifacts/{quote(Path(shot).name)}"
            if shot and (Path(ARTIFACT_DIR) / Path(shot).name).is_file()
            else None
        )
        results_with_urls.append({**res, "screenshot_url": shot_url})

    # Build issue list inline
    issues = []
    for res in results_with_urls:
        vp = res.get("viewport", "desktop")
        metrics = res.get("metrics", {})
        shot_url = res.get("screenshot_url")
        has_offscreen = any(b.get("is_off_screen") for b in metrics.get("buttons", []))
        if metrics.get("has_horizontal_overflow") and not has_offscreen:
            issues.append({"type": "horizontal_overflow", "viewport": vp, "severity": "high" if vp == "mobile" else "medium", "screenshot_url": shot_url, "description": f"Horizontal overflow: scroll_width={metrics.get('scroll_width')}px > client_width={res.get('width')}px"})
        for b in metrics.get("buttons", []):
            if b.get("is_off_screen"):
                issues.append({"type": "offscreen_button", "viewport": vp, "severity": "high", "screenshot_url": shot_url, "description": f"Off-screen button: {b.get('selector')} '{b.get('text')}'", "element": b.get("selector")})
        for broken in metrics.get("broken_images", []):
            issues.append({"type": "broken_image", "viewport": vp, "severity": "medium", "screenshot_url": shot_url, "description": f"Broken image: {broken[:200]}"})
        js_errors = [e for e in res.get("console_errors", []) if e.get("level") == "error"]
        if js_errors:
            issues.append({"type": "console_errors", "viewport": vp, "severity": "medium", "screenshot_url": shot_url, "description": f"{len(js_errors)} JS error(s): {'; '.join(e.get('text','')[:80] for e in js_errors[:3])}"})
        if res.get("network_failures"):
            issues.append({"type": "network_failures", "viewport": vp, "severity": "medium", "screenshot_url": shot_url, "description": f"{len(res['network_failures'])} failed request(s)"})

    return {
        "report_format": "omnisight_scan_report_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scan_id": record.scan_id,
        "url": record.url,
        "status": record.status,
        "viewports": record.viewports,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "completed_at": record.completed_at.isoformat() if record.completed_at else None,
        "error": record.error,
        "captures": results_with_urls,
        "issues": issues,
        "issue_count": len(issues),
        "summary": {
            "total_issues": len(issues),
            "critical": sum(1 for i in issues if i.get("severity") == "critical"),
            "high": sum(1 for i in issues if i.get("severity") == "high"),
            "medium": sum(1 for i in issues if i.get("severity") == "medium"),
            "low": sum(1 for i in issues if i.get("severity") == "low"),
        }
    }
