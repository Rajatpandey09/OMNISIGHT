import os
import asyncio
from fastapi import FastAPI, HTTPException, status
from pydantic import HttpUrl, BaseModel
from playwright.async_api import async_playwright

app = FastAPI(
    title="OmniSight Backend & Browser Automation",
    version="1.0.0",
    description="Backend service for headless navigation and layout metric extraction."
)

# Ensure artifact directory exists for saving viewport screenshots
ARTIFACT_DIR = "artifacts"
os.makedirs(ARTIFACT_DIR, exist_ok=True)

# Fixed allow-list of local/test URLs to prevent SSRF and unauthorized targets[cite: 22]
ALLOWED_DOMAINS = ["localhost", "127.0.0.1", "example.com"]

class ScanRequest(BaseModel):
    url: str
    scan_id: str

def validate_target_url(url: str):
    """Basic security validation to check against allowed domains."""
    if not any(domain in url for domain in ALLOWED_DOMAINS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target URL is not permitted by security policies (SSRF protection)."
        )

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Health check endpoint for CI/CD and dashboard monitoring."""
    return {"status": "healthy", "service": "OmniSight Backend & Browser Automation"}

@app.post("/api/scan", status_code=status.HTTP_200_OK)
async def execute_browser_scan(payload: ScanRequest):
    """
    Opens target URL at desktop and mobile viewports, extracts layout metrics,
    and captures responsive screenshot artifacts.
    """
    validate_target_url(payload.url)
    
    desktop_screenshot_path = os.path.join(ARTIFACT_DIR, f"{payload.scan_id}_desktop.png")
    mobile_screenshot_path = os.path.join(ARTIFACT_DIR, f"{payload.scan_id}_mobile.png")
    
    browser = None
    try:
        async with async_playwright() as p:
            # Launch Chromium browser instance securely
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Navigate to target URL with timeout handling
            await page.goto(payload.url, timeout=30000, wait_until="networkidle")
            
            # --- 1. Desktop Viewport Capture & Analysis ---
            await page.set_viewport_size({"width": 1366, "height": 768})
            await page.screenshot(path=desktop_screenshot_path, full_page=True)
            
            desktop_metrics = await page.evaluate("""() => {
                return {
                    scrollWidth: document.documentElement.scrollWidth,
                    clientWidth: document.documentElement.clientWidth,
                    hasHorizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth
                }
            }""")
            
            # --- 2. Mobile Viewport Capture & Analysis ---
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
                }
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
        # Always guarantee browser resource cleanup in finally blocks[cite: 22]
        if browser:
            await browser.close()