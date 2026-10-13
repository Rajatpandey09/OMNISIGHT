import os
import asyncio
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from playwright.async_api import async_playwright

app = FastAPI(
    title="OmniSight Backend & Browser Automation",
    version="1.1.0",
    description="Backend service with stable schemas for VLM hand-off."
)

ARTIFACT_DIR = "artifacts"
os.makedirs(ARTIFACT_DIR, exist_ok=True)

ALLOWED_DOMAINS = ["localhost", "127.0.0.1", "example.com"]

# --- Pydantic Models for Stable Schema & AI Hand-off ---
class ScanRequest(BaseModel):
    url: str
    scan_id: str

class ElementMetric(BaseModel):
    text: str
    top: float
    left: float
    width: float
    height: float
    isOffScreen: bool

class ViewportMetrics(BaseModel):
    scrollWidth: float
    clientWidth: float
    hasHorizontalOverflow: bool
    interactiveElements: list[ElementMetric] = []

class ScanArtifacts(BaseModel):
    desktop_screenshot: str
    mobile_screenshot: str

class ScanResponse(BaseModel):
    scan_id: str
    url: str
    status: str
    metrics: dict
    artifacts: ScanArtifacts

def validate_target_url(url: str):
    if not any(domain in url for domain in ALLOWED_DOMAINS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target URL is not permitted by security policies (SSRF protection)."
        )

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    return {"status": "healthy", "service": "OmniSight Backend & Browser Automation"}

@app.post("/api/scan", response_model=ScanResponse, status_code=status.HTTP_200_OK)
async def execute_browser_scan(payload: ScanRequest):
    validate_target_url(payload.url)
    
    desktop_screenshot_path = os.path.join(ARTIFACT_DIR, f"{payload.scan_id}_desktop.png")
    mobile_screenshot_path = os.path.join(ARTIFACT_DIR, f"{payload.scan_id}_mobile.png")
    
    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            await page.goto(payload.url, timeout=30000, wait_until="networkidle")
            
            # Desktop Capture & Metrics
            await page.set_viewport_size({"width": 1366, "height": 768})
            await page.screenshot(path=desktop_screenshot_path, full_page=True)
            desktop_metrics = await page.evaluate("""() => ({
                scrollWidth: document.documentElement.scrollWidth,
                clientWidth: document.documentElement.clientWidth,
                hasHorizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
                interactiveElements: []
            })""")
            
            # Mobile Capture & Metrics
            await page.set_viewport_size({"width": 390, "height": 844})
            await page.screenshot(path=mobile_screenshot_path, full_page=True)
            mobile_metrics = await page.evaluate("""() => {
                const buttons = Array.from(document.querySelectorAll('button, a.btn')).map(el => {
                    const rect = el.getBoundingClientRect();
                    return {
                        text: el.innerText.trim(),
                        top: rect.top,
                        left: rect.left,
                        width: rect.width,
                        height: rect.height,
                        isOffScreen: rect.right > window.innerWidth || rect.left < 0
                    };
                });
                return {
                    scrollWidth: document.documentElement.scrollWidth,
                    clientWidth: document.documentElement.clientWidth,
                    hasHorizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
                    interactiveElements: buttons
                };
            }""")

            return {
                "scan_id": payload.scan_id,
                "url": payload.url,
                "status": "success",
                "metrics": {
                    "desktop": desktop_metrics,
                    "mobile": mobile_metrics
                },
                "artifacts": {
                    "desktop_screenshot": desktop_screenshot_path,
                    "mobile_screenshot": mobile_screenshot_path
                }
            }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Browser automation failed: {str(e)}"
        )
    finally:
        if browser:
            await browser.close()