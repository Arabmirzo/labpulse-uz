"""
Alertlar va sozlamalar bo'yicha birlik testlar.
"""
from app.services.alerts import (
    generate_alerts_from_metrics,
    get_alerts,
    acknowledge_alert,
    clear_all_alerts
)


def test_alert_flow():
    clear_all_alerts()

    # Sustained CPU va yuqori RAM simulyatsiyasi
    metrics = {
        "cpu_percent": 95.0,
        "memory": {"used_percent": 94.0, "total_bytes": 16000000000},
        "disk": {"total_bytes": 100000000000, "free_bytes": 5000000000}
    }

    # 1. RAM darhol alert beradi
    alerts = generate_alerts_from_metrics(metrics)
    assert len(alerts) > 0
    ram_alert = next((a for a in alerts if a["key"] == "ram_critical"), None)
    assert ram_alert is not None
    assert ram_alert["level"] == "Muhim"

    # 2. Acknowledge qilish
    alert_id = ram_alert["id"]
    success = acknowledge_alert(alert_id)
    assert success is True

    # 3. Ro'yxatdan tekshirish
    all_alerts = get_alerts()
    ack_alert = next((a for a in all_alerts if a["id"] == alert_id), None)
    assert ack_alert is not None
    assert ack_alert["acknowledged"] is True
