import os
import asyncio
import logging
from fastapi import FastAPI, Request, HTTPException, status
from pydantic import BaseModel
from playwright.async_api import async_playwright

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omnisight_backend")

app = FastAPI(
    title="OmniSight Backend & Browser Automation",
    version="1.3.0",
    description="Backend service aligned with teammate VLM/AI prompt schema."
)

ARTIFACT_DIR = "artifacts"
os.makedirs(ARTIFACT_DIR, exist_ok=True)

ALLOWED_DOMAINS = ["localhost", "127.0.0.1", "example.com"]

class ScanRequest(BaseModel):
    url: str
    scan_id: str

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = asyncio.get_event_loop().time()
    response = await call_next(request)
    process_time = asyncio.get_event_loop().time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"Path: {request.url.path} | Method: {request.method} | Duration: {process_time:.4f}s | Status: {response.status_code}")
    return response

@app.get("/", status_code=status.HTTP_200_OK)
def read_root():
    return {
        "service": "OmniSight Backend & Browser Automation",
        "status": "active",
        "docs": "/docs",
        "role": "Member 2 - Backend & Browser Automation"
    }

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    return {"status": "healthy", "service": "OmniSight Backend"}

@app.post("/api/scan", status_code=status.HTTP_200_OK)
async def execute_browser_scan(payload: ScanRequest):
    if not any(domain in payload.url for domain in ALLOWED_DOMAINS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target URL is not permitted by security policies (SSRF protection)."
        )
    
    desktop_screenshot_filename = f"{payload.scan_id}_desktop.png"
    mobile_screenshot_filename = f"{payload.scan_id}_mobile.png"
    
    desktop_screenshot_path = os.path.join(ARTIFACT_DIR, desktop_screenshot_filename)
    mobile_screenshot_path = os.path.join(ARTIFACT_DIR, mobile_screenshot_filename)
    
    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            await page.goto(payload.url, timeout=30000, wait_until="networkidle")
            
            # --- Desktop Viewport Capture ---
            await page.set_viewport_size({"width": 1366, "height": 768})
            await page.screenshot(path=desktop_screenshot_path, full_page=True)
            
            desktop_metrics = await page.evaluate("""() => {
                const hiddenElements = Array.from(document.querySelectorAll('[hidden], .hidden, [style*="display: none"]'))
                    .map(el => el.id || el.className || 'unnamed_control');
                return {
                    scroll_width: document.documentElement.scrollWidth,
                    scroll_height: document.documentElement.scrollHeight,
                    has_horizontal_overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
                    buttons: [],
                    hidden_controls: hiddenElements
                };
            }""")
            
            # --- Mobile Viewport Capture ---
            await page.set_viewport_size({"width": 390, "height": 844})
            await page.screenshot(path=mobile_screenshot_path, full_page=True)
            
            mobile_metrics = await page.evaluate("""() => {
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

            # Formatted response matching teammate's expected schema
            return {
                "scan_id": payload.scan_id,
                "results": [
                    {
                        "viewport": "desktop",
                        "width": 1366,
                        "height": 768,
                        "screenshot": desktop_screenshot_filename,
                        "metrics": desktop_metrics
                    },
                    {
                        "viewport": "mobile",
                        "width": 390,
                        "height": 844,
                        "screenshot": mobile_screenshot_filename,
                        "metrics": mobile_metrics
                    }
                ]
            }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Browser automation failed: {str(e)}"
        )
    finally:
        if browser:
            await browser.close()