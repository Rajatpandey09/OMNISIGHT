from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "OmniSight Backend & Browser Automation"

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "OmniSight Backend"}

def test_scan_ssrf_protection():
    # Test that unauthorized external domains are blocked by security policy
    response = client.post("/api/scan", json={
        "url": "https://malicious-external-site.com",
        "scan_id": "test-ssrf-001"
    })
    assert response.status_code == 400
    assert "not is not permitted" in response.json()["detail"] or "SSRF" in response.json()["detail"]