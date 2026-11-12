"""Masofaviy qurilma holati ogohlantirishlari testlari."""
from app.services.alerts import acknowledge_alert, get_alerts
from app.services.device_monitoring import (
    check_device_status_transitions,
    get_device_status_alerts,
)
from app.services.organizations import (
    create_organization,
    delete_organization,
    get_db,
    record_device_telemetry,
)


def test_offline_and_recovery_events_are_persisted():
    org = create_organization(name="Device Status Test")
    device_id = "device-status-test"
    try:
        record_device_telemetry(org["id"], {
            "device_id": device_id,
            "hostname": "Test Classroom PC",
        })
        with get_db() as conn:
            last_seen = conn.execute(
                "SELECT last_seen FROM remote_devices WHERE id = ?",
                (device_id,)
            ).fetchone()["last_seen"]

        assert check_device_status_transitions(now=last_seen) == []

        offline_time = last_seen + 36
        offline_events = check_device_status_transitions(now=offline_time)
        assert len(offline_events) == 1
        assert offline_events[0]["key"] == "device_offline"
        assert offline_events[0]["level"] == "Muhim"
        assert offline_events[0]["id"] in {
            event["id"] for event in get_alerts()
        }

        assert acknowledge_alert(offline_events[0]["id"]) is True
        assert offline_events[0]["id"] not in {
            event["id"] for event in get_alerts(only_unacknowledged=True)
        }
        stored_offline = next(
            event for event in get_device_status_alerts()
            if event["id"] == offline_events[0]["id"]
        )
        assert stored_offline["acknowledged"] is True

        recovered_time = offline_time + 1
        with get_db() as conn:
            conn.execute(
                "UPDATE remote_devices SET last_seen = ? WHERE id = ?",
                (recovered_time, device_id)
            )
        recovery_events = check_device_status_transitions(now=recovered_time)
        assert len(recovery_events) == 1
        assert recovery_events[0]["key"] == "device_recovered"
        assert recovery_events[0]["level"] == "Ma'lumot"
    finally:
        delete_organization(org["id"])
