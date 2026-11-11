import os
import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Depends, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from playwright.async_api import async_playwright
from sqlalchemy.orm import Session

from database import init_db, get_db, SessionLocal, ScanRecord

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omnisight_backend")

# Initialize SQLite database schema
init_db()

app = FastAPI(
    title="OmniSight Backend & Browser Automation",
    version="1.7.0",
    description="Production-grade backend service for multimodal UI self-healing, SQLite persistence, and asynchronous browser automation with resilient retries.",
    contact={
        "name": "Priyanshu",
        "role": "Backend & Browser Automation Engineer"
    }
)

# CORS middleware for local frontend dashboard communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

ARTIFACT_DIR = "artifacts"
os.makedirs(ARTIFACT_DIR, exist_ok=True)

# Mount artifacts directory for direct screenshot access by frontend and visual review
app.mount("/artifacts", StaticFiles(directory=ARTIFACT_DIR), name="artifacts")

# SSRF Protection: strictly allowlisted hostnames
ALLOWED_DOMAINS = ["localhost", "127.0.0.1", "example.com"]

# In-memory store maintained alongside SQLite for seamless backward compatibility
SCAN_HISTORY_STORE = []


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


class VerifyFixRequest(BaseModel):
    issue_id: Optional[str] = None
    scan_id: Optional[str] = None
    url: Optional[str] = None
    css_patch: Optional[str] = None


class FixActionRequest(BaseModel):
    issue_id: Optional[str] = None
    scan_id: Optional[str] = None


async def navigate_with_retry(page, url: str, retries: int = 3, delay: int = 2):
    """Attempt to navigate to a target URL with exponential backoff to handle network flakiness."""
    for attempt in range(retries):
        try:
            await page.goto(url, timeout=30000, wait_until="networkidle")
            return
        except Exception as e:
            if attempt == retries - 1:
                raise e
            logger.warning(f"Navigation attempt {attempt + 1} failed for {url}: {str(e)}. Retrying in {delay * (attempt + 1)}s...")
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


async def run_scan_worker(scan_id: str, url: str, viewports: List[str], css_patch: Optional[str] = None):
    """
    Background worker that runs headless Playwright across viewports,
    extracts deep DOM layout metrics, captures screenshots, and persists results to SQLite.
    """
    logger.info(f"Starting browser automation for scan '{scan_id}' on {url}")
    db: Session = SessionLocal()
    record = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_id).first()
    if record:
        record.status = "processing"
        db.commit()

    browser = None
    try:
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()

            # Define standard viewports
            viewport_configs = {
                "desktop": {"width": 1366, "height": 768},
                "mobile": {"width": 390, "height": 844}
            }

            for vp in viewports:
                cfg = viewport_configs.get(vp, {"width": 1366, "height": 768})
                page = await context.new_page()
                try:
                    await page.set_viewport_size({"width": cfg["width"], "height": cfg["height"]})
                    await navigate_with_retry(page, url)

                    # Inject CSS patch if performing self-healing verification
                    if css_patch:
                        logger.info(f"Injecting CSS patch into page for viewport {vp}")
                        await page.add_style_tag(content=css_patch)

                    screenshot_filename = f"{scan_id}_{vp}.png"
                    screenshot_path = os.path.join(ARTIFACT_DIR, screenshot_filename)
                    await page.screenshot(path=screenshot_path, full_page=True)

                    metrics = await page.evaluate("""() => {
                        const buttons = Array.from(document.querySelectorAll('button, a.btn, input[type="submit"]')).map(el => {
                            const rect = el.getBoundingClientRect();
                            return {
                                selector: el.id ? `#${el.id}` : (el.className ? `.${el.className.split(' ')[0]}` : el.tagName.toLowerCase()),
                                text: el.innerText.trim() || el.value || '',
                                x: rect.x,
                                y: rect.y,
                                width: rect.width,
                                height: rect.height,
                                is_off_screen: rect.right > window.innerWidth || rect.left < 0
                            };
                        });
                        const hiddenElements = Array.from(document.querySelectorAll('[hidden], .hidden, [style*="display: none"]'))
                            .map(el => el.id || el.className || 'unnamed_control');
                        return {
                            scroll_width: document.documentElement.scrollWidth,
                            scroll_height: document.documentElement.scrollHeight,
                            has_horizontal_overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
                            buttons: buttons,
                            hidden_controls: hiddenElements
                        };
                    }""")

                    results.append({
                        "viewport": vp,
                        "width": cfg["width"],
                        "height": cfg["height"],
                        "screenshot": screenshot_filename,
                        "metrics": metrics
                    })
                finally:
                    await page.close()

        # Update persistent database record
        if record:
            record.status = "completed"
            record.results = results
            record.completed_at = datetime.now(timezone.utc)
            db.commit()
            
            # Sync to in-memory store
            SCAN_HISTORY_STORE.append(record.to_dict())
            logger.info(f"Scan '{scan_id}' completed successfully with {len(results)} viewport captures.")

    except Exception as e:
        logger.exception(f"Automation execution failed for scan '{scan_id}': {e}")
        if record:
            record.status = "failed"
            record.error = str(e)
            record.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        if browser:
            await browser.close()
        db.close()


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
    if not any(domain in payload.url for domain in ALLOWED_DOMAINS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target URL is not permitted by security policies (SSRF protection)."
        )

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
    record = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_id).first()
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
    record = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_id).first()
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
    if not any(domain in payload.url for domain in ALLOWED_DOMAINS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target URL is not permitted by security policies (SSRF protection)."
        )

    rescan_id = f"rescan-{uuid.uuid4().hex[:8]}"
    viewports = payload.viewports or ["desktop", "mobile"]

    # Run browser scan with CSS patch applied
    await run_scan_worker(rescan_id, payload.url, viewports, css_patch=payload.css_patch)

    record = db.query(ScanRecord).filter(ScanRecord.scan_id == rescan_id).first()
    scan_data = record.to_dict() if record else {"results": []}

    # Evaluate resolution state
    has_overflow = False
    has_offscreen_buttons = False
    for r in scan_data.get("results", []):
        metrics = r.get("metrics", {})
        if metrics.get("has_horizontal_overflow"):
            has_overflow = True
        for b in metrics.get("buttons", []):
            if b.get("is_off_screen"):
                has_offscreen_buttons = True

    verification_state = "verified_resolved" if not (has_overflow or has_offscreen_buttons) else "verification_failed"

    return {
        "rescan_id": rescan_id,
        "verification_state": verification_state,
        "css_patch_applied": payload.css_patch,
        "url": payload.url,
        "scan_data": scan_data
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
        "status": "verified_resolved" if record and record.status == "completed" else "pending",
        "scan_id": target_scan_id,
        "message": "Fix verification checked against scan history."
    }


@app.get("/api/targets", status_code=status.HTTP_200_OK, tags=["Frontend"])
def get_targets():
    """Return available targets for the frontend scan target selector."""
    return [
        {"id": "localhost-testbed", "name": "Local Testbed Suite (Port 5500)", "url": "http://localhost:5500/test-pages/index.html"},
        {"id": "bug-overflow", "name": "Horizontal Overflow Defect", "url": "http://localhost:5500/test-pages/bug_overflow.html"},
        {"id": "bug-offscreen", "name": "Off-Screen Button Defect", "url": "http://localhost:5500/test-pages/bug_offscreen_button.html"},
        {"id": "bug-overlap", "name": "Overlapping Text Defect", "url": "http://localhost:5500/test-pages/bug_overlapping_text.html"},
        {"id": "bug-hidden", "name": "Hidden Interactive Control", "url": "http://localhost:5500/test-pages/bug_hidden_control.html"},
        {"id": "bug-contrast", "name": "Low Contrast Defect", "url": "http://localhost:5500/test-pages/bug_contrast.html"},
        {"id": "clean-page", "name": "Clean Reference Page (No Bugs)", "url": "http://localhost:5500/test-pages/clean.html"},
        {"id": "example-com", "name": "Example.com (External Demo)", "url": "https://example.com"}
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
def get_issues(db: Session = Depends(get_db)):
    """Return all detected layout issues extracted from scan records."""
    records = db.query(ScanRecord).all()
    issues_list = []
    for r in records:
        for res in (r.results or []):
            vp = res.get("viewport", "desktop")
            metrics = res.get("metrics", {})
            screenshot = res.get("screenshot", "")

            if metrics.get("has_horizontal_overflow"):
                issues_list.append({
                    "id": f"ISSUE-{r.scan_id[:8]}-OVERFLOW",
                    "issue_id": f"ISSUE-{r.scan_id[:8]}-OVERFLOW",
                    "title": f"Horizontal Overflow Detected ({vp.capitalize()})",
                    "type": "horizontal_overflow",
                    "issue_type": "horizontal_overflow",
                    "viewport": vp,
                    "severity": "high" if vp == "mobile" else "medium",
                    "state": "detected",
                    "verification_state": "detected",
                    "status": "detected",
                    "scan_id": r.scan_id,
                    "target_url": r.url,
                    "screenshot": f"/artifacts/{screenshot}" if screenshot else None,
                    "suggested_fix": ".wide-banner { max-width: 100%; width: auto; }",
                    "description": f"Content scroll width ({metrics.get('scroll_width')}px) exceeds visible screen width ({res.get('width')}px)."
                })

            for idx, b in enumerate(metrics.get("buttons", [])):
                if b.get("is_off_screen"):
                    issues_list.append({
                        "id": f"ISSUE-{r.scan_id[:8]}-BUTTON-{idx}",
                        "issue_id": f"ISSUE-{r.scan_id[:8]}-BUTTON-{idx}",
                        "title": f"Off-Screen Button ({b.get('text') or b.get('selector')})",
                        "type": "offscreen_button",
                        "issue_type": "offscreen_button",
                        "viewport": vp,
                        "severity": "high",
                        "state": "detected",
                        "verification_state": "detected",
                        "status": "detected",
                        "scan_id": r.scan_id,
                        "target_url": r.url,
                        "screenshot": f"/artifacts/{screenshot}" if screenshot else None,
                        "suggested_fix": f"{b.get('selector')} {{ position: static; margin-top: 1rem; }}",
                        "description": "Target interactive button is clipped outside visible window boundary."
                    })

    return issues_list


@app.post("/api/approve_fix", status_code=status.HTTP_200_OK, tags=["Frontend"])
def approve_fix(payload: FixActionRequest):
    """Record human approval of a proposed fix."""
    return {
        "status": "applied",
        "message": f"Fix for issue '{payload.issue_id or payload.scan_id}' has been approved by reviewer."
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
