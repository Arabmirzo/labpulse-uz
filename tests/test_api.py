"""
FastAPI Marshrutlari va Sahifalarini tekshirish uchun testlar.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "LabPulse UZ"


def test_api_metrics():
    res = client.get("/api/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "cpu_percent" in data
    assert "memory" in data
    assert "disk" in data


def test_api_history():
    res = client.get("/api/history")
    assert res.status_code == 200
    assert "history" in res.json()


def test_pages_and_static_assets():
    # Sahifalar 200 qaytarishi kerak
    pages = ["/", "/devices", "/diagnostics", "/alerts", "/reports", "/settings"]
    for path in pages:
        res = client.get(path)
        assert res.status_code == 200, f"Sahifa ochilmadi: {path}"
        assert "text/html" in res.headers["content-type"]

    # Statik fayllar 404 bermasligi kerak
    assets = [
        "/static/css/app.css",
        "/static/js/app.js",
        "/static/js/dashboard.js",
        "/static/js/diagnostics.js",
        "/static/assets/logo.svg"
    ]
    for asset in assets:
        res = client.get(asset)
        assert res.status_code == 200, f"Statik fayl topilmadi: {asset}"


def test_reports_lifecycle():
    # 1. Hisobot yaratish
    res = client.post("/api/reports", json={"note": "Test hisobot"})
    assert res.status_code == 200
    report = res.json()
    report_id = report["id"]
    assert "summary" in report

    # 2. Chop etish sahifasi ko'rinishi
    view_res = client.get(f"/reports/{report_id}/view")
    assert view_res.status_code == 200
    assert "LabPulse UZ Diagnostika Hisoboti" in view_res.text

    # 3. JSON download
    dl_res = client.get(f"/api/reports/{report_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/json"


def test_settings_validation():
    # Noto'g'ri interval (faqat 3, 5, 10, 30 mumkin)
    bad_res = client.put("/api/settings", json={"refresh_interval": 99})
    assert bad_res.status_code == 400

    # Noto'g'ri target (injeksiya xavfi)
    bad_res2 = client.put("/api/settings", json={"diagnostic_target": "bad;ls"})
    assert bad_res2.status_code == 400

    # To'g'ri yangilanish
    good_res = client.put("/api/settings", json={"refresh_interval": 10, "diagnostic_target": "1.1.1.1"})
    assert good_res.status_code == 200
    assert good_res.json()["settings"]["refresh_interval"] == 10
