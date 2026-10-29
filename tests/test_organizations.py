"""
Tashkilotlar va Masofaviy Ingestion testlari.
"""
from fastapi.testclient import TestClient
from app.main import app
from app.services.organizations import (
    create_organization,
    get_organization_by_key,
    record_device_telemetry,
    get_devices_by_org,
    delete_organization
)

client = TestClient(app)


def test_organization_crud():
    org = create_organization(name="Unit Test Akademiya", contact_email="test@akademiya.uz", plan="Pro")
    assert org["id"].startswith("org_")
    assert org["api_key"].startswith("lp_live_")

    found = get_organization_by_key(org["api_key"])
    assert found is not None
    assert found["name"] == "Unit Test Akademiya"

    # API orqali ro'yxatni olish
    res = client.get("/api/v1/organizations")
    assert res.status_code == 200
    org_list = res.json()["organizations"]
    assert any(o["id"] == org["id"] for o in org_list)

    # Tozalash
    delete_organization(org["id"])


def test_agent_heartbeat_api():
    # 1. Kompaniya yaratish
    org = create_organization(name="Heartbeat Test Corp", plan="Standard")
    api_key = org["api_key"]

    # 2. Agentdan heartbeat yuborish
    payload = {
        "device_id": "PC-TEST-007",
        "hostname": "Test-Talaba-PC",
        "platform": "Windows 11",
        "ip_address": "192.168.1.55",
        "cpu_percent": 42.5,
        "memory": {"used_percent": 55.0, "total_bytes": 8000000000},
        "disk": {"used_percent": 40.0, "total_bytes": 256000000000, "free_bytes": 150000000000},
        "uptime_seconds": 7200
    }

    res = client.post("/api/v1/agent/heartbeat", json=payload, headers={"X-LabPulse-Key": api_key})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["ack"] is True
    assert data["device_id"] == "PC-TEST-007"

    # 3. Qurilmalar ro'yxatida ko'rinishi
    dev_res = client.get(f"/api/v1/devices?org_id={org['id']}")
    assert dev_res.status_code == 200
    devs = dev_res.json()["devices"]
    assert len(devs) == 1
    assert devs[0]["hostname"] == "Test-Talaba-PC"
    assert devs[0]["is_online"] is True

    # 4. Noto'g'ri kalit rad etilishi kerak
    bad_res = client.post("/api/v1/agent/heartbeat", json=payload, headers={"X-LabPulse-Key": "wrong_key"})
    assert bad_res.status_code == 403

    # 5. Qo'lda kompyuter qo'shish (Manual Add) testi
    man_res = client.post("/api/v1/devices/manual", json={
        "org_id": org["id"],
        "hostname": "Manual-Audit-PC",
        "ip_address": "192.168.1.99",
        "platform": "Windows 11 Pro"
    })
    assert man_res.status_code == 200
    assert man_res.json()["status"] == "success"

    # 6. O'rnatgich skripti (Installer batch script) testi
    script_res = client.get(f"/api/v1/agent/installer-script?org_id={org['id']}")
    assert script_res.status_code == 200
    assert "labpulse_agent.py" in script_res.text
    assert api_key in script_res.text

    # Tozalash
    delete_organization(org["id"])
