import importlib.util
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def _load_backend_app():
    """Load backend/main.py under its own module name, so it can't be mixed up
    with the root main.py that other test files import as `main`."""
    spec = importlib.util.spec_from_file_location("backend_main", BACKEND / "main.py")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(BACKEND))  # in case backend/main.py imports sibling modules
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(BACKEND))
    return module.app


app = _load_backend_app()
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
