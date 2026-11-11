"""Integrated vision analysis and isolated self-healing API for OmniSight.

These routes connect the existing, tested vision modules to the canonical FastAPI
scanner. Patches are injected only into a disposable Playwright page; no target
source files are edited and no GitHub PR is opened automatically.
"""
import asyncio
import json
import os
import re
import uuid
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db, ScanRecord
from vision.factory import get_provider
from vision.pipeline import analyze_scan
from vision.heal import heal, Rescan

router = APIRouter(prefix="/api/ai", tags=["Vision AI", "Self-Healing"])
ARTIFACT_DIR = Path(os.getenv("ARTIFACT_DIR", "artifacts"))
ALLOWED_TARGET_HOSTS = {"localhost", "127.0.0.1", "example.com"}


class VisionVerifyRequest(BaseModel):
    rescan_id: str = Field(min_length=1, max_length=64)
    viewport: str = Field(default="mobile", pattern="^(desktop|mobile)$")
    issue_type: str = Field(min_length=1, max_length=40)
    element: str = Field(default="", max_length=200)


class HealRequest(BaseModel):
    finding_index: int = Field(default=0, ge=0, le=100)
    viewport: str = Field(default="mobile", pattern="^(desktop|mobile)$")
    max_attempts: int = Field(default=2, ge=1, le=3)


def _record_or_404(db: Session, scan_id: str) -> ScanRecord:
    record = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Scan not found.")
    if record.status != "completed":
        raise HTTPException(status_code=409, detail=f"Scan is {record.status}; wait until it completes.")
    return record


def _safe_target(url: str) -> None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme not in {"http", "https"} or host not in ALLOWED_TARGET_HOSTS or parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="AI healing is restricted to the configured local demo allow-list.")


def _input_file(record: ScanRecord) -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for item in (record.results or []):
        shot = Path(str(item.get("screenshot") or "")).name
        if not shot or not (ARTIFACT_DIR / shot).is_file():
            continue
        items.append({
            "viewport": item.get("viewport"),
            "width": item.get("width"),
            "height": item.get("height"),
            "screenshot": shot,
            "metrics": item.get("metrics") or {},
            "relevant_html": item.get("relevant_html") or "",
        })
    if not items:
        raise HTTPException(status_code=422, detail="No usable screenshot artifacts exist for this scan.")
    path = ARTIFACT_DIR / f"{record.scan_id}_vision_input.json"
    path.write_text(json.dumps({"scan_id": record.scan_id, "results": items}), encoding="utf-8")
    return path


def _metrics_fixed(issue_type: str, selector: str, metrics: dict) -> bool | None:
    buttons = metrics.get("buttons") or []
    if issue_type == "horizontal_overflow":
        return metrics.get("has_horizontal_overflow") is False
    if issue_type == "offscreen_button":
        relevant = [b for b in buttons if not selector or b.get("selector") == selector]
        if not relevant:
            relevant = buttons  # Model descriptions are not always literal CSS selectors.
        return bool(relevant) and not any(b.get("is_off_screen") for b in relevant)
    if issue_type == "hidden_control":
        hidden = [str(x) for x in metrics.get("hidden_controls") or []]
        return not any(selector and selector.lstrip("#.") in item for item in hidden)
    return None


def _apply_in_isolated_browser(url: str, viewport: str, css: str, selector: str,
                               issue_type: str, width: int, height: int) -> Rescan:
    from playwright.sync_api import sync_playwright
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.add_style_tag(content=css)
            page.wait_for_timeout(300)
            after_path = ARTIFACT_DIR / f"heal_{uuid.uuid4().hex[:10]}_{viewport}.png"
            after_png = page.screenshot(path=str(after_path), full_page=True)
            metrics = page.evaluate("""() => ({
              has_horizontal_overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
              buttons: Array.from(document.querySelectorAll('button,a.btn,input[type="submit"]')).map(el => {
                const r=el.getBoundingClientRect();
                return {selector:el.id ? '#'+el.id : (el.classList.length ? '.'+el.classList[0] : el.tagName.toLowerCase()),
                  is_off_screen:r.right>innerWidth || r.left<0};
              }),
              hidden_controls:Array.from(document.querySelectorAll('button,input,select,textarea,a')).filter(el=>{
                const s=getComputedStyle(el),r=el.getBoundingClientRect();
                return s.display==='none'||s.visibility==='hidden'||r.width===0||r.height===0;
              }).map(el=>el.id||el.className||el.tagName.toLowerCase())
            })""")
            fixed = _metrics_fixed(issue_type, selector, metrics)
            return Rescan(after_png=after_png, metrics_fixed=fixed)
        finally:
            browser.close()


@router.post("/analyze/{scan_id}")
async def analyze_existing_scan(scan_id: str, screenshot_only: bool = False, db: Session = Depends(get_db)):
    """Run the configured VLM on the actual Playwright screenshots + DOM metrics."""
    record = _record_or_404(db, scan_id)
    path = _input_file(record)
    output = ARTIFACT_DIR / f"{scan_id}_analysis.json"
    try:
        result = await asyncio.to_thread(
            analyze_scan, get_provider(), path, output, 180.0, screenshot_only
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Vision analysis failed: {type(exc).__name__}: {str(exc)[:300]}")
    return result


@router.post("/heal/{scan_id}")
async def heal_existing_scan(scan_id: str, payload: HealRequest, db: Session = Depends(get_db)):
    """Run Plan→Execute→Evaluate with human approval retained outside this endpoint."""
    record = _record_or_404(db, scan_id)
    _safe_target(record.url)
    analysis_path = ARTIFACT_DIR / f"{scan_id}_analysis.json"
    if not analysis_path.is_file():
        raise HTTPException(status_code=409, detail="Run POST /api/ai/analyze/{scan_id} before requesting a fix.")
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    selected = next((a for a in analysis.get("analyses", []) if a.get("viewport") == payload.viewport), None)
    if not selected or selected.get("outcome") != "ok":
        raise HTTPException(status_code=422, detail="No valid VLM analysis exists for the selected viewport.")
    findings = selected.get("findings") or []
    if payload.finding_index >= len(findings):
        raise HTTPException(status_code=404, detail="Finding index does not exist in this viewport analysis.")
    finding = findings[payload.finding_index]
    source = next((x for x in (record.results or []) if x.get("viewport") == payload.viewport), None)
    if not source:
        raise HTTPException(status_code=404, detail="Original viewport capture is missing.")
    screenshot_name = Path(str(source.get("screenshot") or "")).name
    screenshot_path = ARTIFACT_DIR / screenshot_name
    if not screenshot_path.is_file():
        raise HTTPException(status_code=404, detail="Original screenshot artifact is missing.")
    selector = str(finding.get("element") or "")
    issue_type = str(finding.get("issue_type") or "other")
    width, height = int(source.get("width") or 390), int(source.get("height") or 844)

    def apply_and_rescan(css: str):
        return _apply_in_isolated_browser(record.url, payload.viewport, css, selector,
                                          issue_type, width, height)

    result = await asyncio.to_thread(
        heal, get_provider(), finding, screenshot_path.read_bytes(),
        scan_id=scan_id, viewport=payload.viewport, width=width, height=height,
        apply_and_rescan=apply_and_rescan, html=source.get("relevant_html"),
        max_attempts=payload.max_attempts, timeout=180.0
    )
    return {
        **result.to_dict(),
        "human_approval_required": True,
        "source_page_modified": False,
        "note": "The CSS was tested only in a disposable Playwright browser context. Review and explicitly approve any real source change separately."
    }


@router.post("/verify/{scan_id}")
async def verify_user_approved_patch(scan_id: str, payload: VisionVerifyRequest, db: Session = Depends(get_db)):
    """VLM + metrics verification for a human-approved patch rescan."""
    from vision.patches import verify_fix, combine_verdicts
    original = _record_or_404(db, scan_id)
    followup = _record_or_404(db, payload.rescan_id)
    if original.url != followup.url:
        raise HTTPException(status_code=400, detail="Follow-up scan target does not match the original scan.")
    before = next((x for x in (original.results or []) if x.get("viewport") == payload.viewport), None)
    after = next((x for x in (followup.results or []) if x.get("viewport") == payload.viewport), None)
    if not before or not after:
        raise HTTPException(status_code=422, detail="Both original and follow-up viewport captures are required.")
    before_path = ARTIFACT_DIR / Path(str(before.get("screenshot") or "")).name
    after_path = ARTIFACT_DIR / Path(str(after.get("screenshot") or "")).name
    if not before_path.is_file() or not after_path.is_file():
        raise HTTPException(status_code=404, detail="Before/after screenshot artifact is missing.")
    metrics_fixed = _metrics_fixed(payload.issue_type, payload.element, after.get("metrics") or {})
    check = await asyncio.to_thread(
        verify_fix, get_provider(), before_path.read_bytes(), after_path.read_bytes(),
        issue_type=payload.issue_type, element=payload.element, scan_id=scan_id,
        viewport=payload.viewport, timeout=180.0
    )
    model_verdict = check.verdict if check.outcome == "ok" else "inconclusive"
    final, reason = combine_verdicts(model_verdict, metrics_fixed, check.new_problems if check.outcome == "ok" else "none")
    state = "verified_resolved" if final == "fixed" else ("verification_failed" if final == "not_fixed" else "inconclusive")
    return {
        "scan_id": scan_id, "rescan_id": payload.rescan_id, "viewport": payload.viewport,
        "verification_state": state, "model_outcome": check.outcome,
        "model_verdict": model_verdict, "model_confidence": check.confidence,
        "model_evidence": check.evidence, "metrics_fixed": metrics_fixed,
        "new_problems": check.new_problems, "reason": reason,
        "before_screenshot": before_path.name, "after_screenshot": after_path.name,
        "source_page_modified": False
    }
