import os
import uuid
import pytest
from fastapi.testclient import TestClient
from main import app, ARTIFACT_DIR
from database import SessionLocal, ScanRecord, init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    yield

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
    detail = response.json()["detail"].lower()
    assert "not permitted" in detail or "ssrf" in detail

def test_async_scan_creation_returns_202(monkeypatch):
    # Mock worker so test runs instantly without network timeout
    async def mock_worker(*args, **kwargs):
        pass
    monkeypatch.setattr("main.run_scan_worker", mock_worker)

    # Test that scan requests to permitted domains return 202 Accepted and create pending record
    test_scan_id = f"test-async-{uuid.uuid4().hex[:6]}"
    response = client.post("/api/scan", json={
        "url": "http://localhost:8000",
        "scan_id": test_scan_id,
        "viewports": ["desktop", "mobile"]
    })
    assert response.status_code == 202
    data = response.json()
    assert data["scan_id"] == test_scan_id
    assert data["status"] == "pending"
    assert "Poll /api/scans" in data["message"]
    assert data["viewports"] == ["desktop", "mobile"]

def test_scan_status_polling_endpoints():
    test_scan_id = f"test-poll-{uuid.uuid4().hex[:6]}"
    
    # 404 for nonexistent scan
    res_404 = client.get(f"/api/scans/{test_scan_id}")
    assert res_404.status_code == 404

    # Create record in DB
    db = SessionLocal()
    try:
        record = ScanRecord(
            scan_id=test_scan_id,
            url="http://127.0.0.1:8000",
            status="completed",
            viewports=["desktop"],
            results=[{
                "viewport": "desktop",
                "width": 1366,
                "height": 768,
                "screenshot": "dummy_desktop.png",
                "metrics": {"has_horizontal_overflow": False, "buttons": []}
            }]
        )
        db.add(record)
        db.commit()
    finally:
        db.close()

    # Now poll status
    res_200 = client.get(f"/api/scans/{test_scan_id}")
    assert res_200.status_code == 200
    data = res_200.json()
    assert data["scan_id"] == test_scan_id
    assert data["status"] == "completed"
    assert len(data["results"]) == 1

def test_scan_history_endpoint():
    response = client.get("/api/scans")
    assert response.status_code == 200
    data = response.json()
    assert "scans" in data
    assert "items" in data
    assert "total" in data
    assert isinstance(data["scans"], list)

def test_database_persistence_model_to_dict():
    test_id = f"test-model-{uuid.uuid4().hex[:6]}"
    db = SessionLocal()
    try:
        record = ScanRecord(
            scan_id=test_id,
            url="http://127.0.0.1:5500",
            status="completed",
            viewports=["desktop", "mobile"],
            results=[
                {
                    "viewport": "mobile",
                    "metrics": {
                        "has_horizontal_overflow": True,
                        "buttons": [{"is_off_screen": True}]
                    }
                }
            ]
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        d = record.to_dict()
        assert d["scan_id"] == test_id
        assert d["issue_count"] == 2  # 1 overflow + 1 offscreen button
        assert d["status"] == "completed"
    finally:
        db.close()

def test_delete_scan_endpoint():
    test_id = f"test-delete-{uuid.uuid4().hex[:6]}"
    db = SessionLocal()
    try:
        record = ScanRecord(
            scan_id=test_id,
            url="http://localhost:8000",
            status="pending"
        )
        db.add(record)
        db.commit()
    finally:
        db.close()

    # Delete existing
    del_res = client.delete(f"/api/scans/{test_id}")
    assert del_res.status_code == 200
    assert "deleted" in del_res.json()["message"].lower()

    # Deleting again returns 404
    del_res_again = client.delete(f"/api/scans/{test_id}")
    assert del_res_again.status_code == 404

def test_rescan_ssrf_protection():
    response = client.post("/api/rescan", json={
        "url": "http://evil-external-site.com",
        "css_patch": "body { overflow-x: hidden; }"
    })
    assert response.status_code == 400

def test_rescan_endpoint_success(monkeypatch):
    async def mock_worker(scan_id, url, viewports, css_patch=None):
        db = SessionLocal()
        try:
            record = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_id).first()
            if record:
                record.status = "completed"
                record.results = [{"viewport": "desktop", "metrics": {"has_horizontal_overflow": False, "buttons": []}}]
                db.commit()
        finally:
            db.close()
    monkeypatch.setattr("main.run_scan_worker", mock_worker)

    response = client.post("/api/rescan", json={
        "url": "http://localhost:8000",
        "css_patch": "body { overflow-x: hidden; }"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["verification_state"] == "verified_resolved"
    assert data["css_patch_applied"] == "body { overflow-x: hidden; }"

def test_verify_fix_endpoint():
    test_id = f"test-verify-{uuid.uuid4().hex[:6]}"
    db = SessionLocal()
    try:
        record = ScanRecord(
            scan_id=test_id,
            url="http://localhost:8000",
            status="completed"
        )
        db.add(record)
        db.commit()
    finally:
        db.close()

    res = client.post("/api/verify_fix", json={"scan_id": test_id})
    assert res.status_code == 200
    assert res.json()["status"] == "verified_resolved"

def test_artifacts_endpoints():
    # Test list artifacts
    res = client.get("/api/artifacts")
    assert res.status_code == 200
    assert "artifacts" in res.json()
    assert "total_files" in res.json()

    # Test clean artifacts
    clean_res = client.delete("/api/artifacts/clean")
    assert clean_res.status_code == 200
    assert "deleted" in clean_res.json()["message"].lower() or "exist" in clean_res.json()["message"].lower()
