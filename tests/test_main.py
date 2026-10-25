
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from main import app

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "OmniSight Backend & Browser Automation"


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "OmniSight Backend",
    }

def test_scan_rejects_unauthorized_domain():
    response = client.post(
        "/api/scan",
        json={
            "url": "https://malicious-external-site.com",
            "viewports": ["desktop", "mobile"],
        },
    )

    assert response.status_code == 400

def test_scan_history_endpoint():
    response = client.get("/api/scans")
    assert response.status_code == 200
