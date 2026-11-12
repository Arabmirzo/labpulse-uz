"""Masofaviy qurilmalar holati va doimiy status ogohlantirishlari."""
import time
import uuid
from contextlib import closing
from typing import Any, Dict, List, Optional

from app.services.organizations import (
    DEVICE_OFFLINE_AFTER_SECONDS,
    get_db,
)

DEVICE_STATUS_CHECK_INTERVAL_SECONDS = 5
MAX_DEVICE_STATUS_EVENTS = 1000


def check_device_status_transitions(now: Optional[float] = None) -> List[Dict[str, Any]]:
    """Qurilmalar holatini tekshiradi va status o'zgarsa SQLite'ga qayd etadi."""
    checked_at = time.time() if now is None else now
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(checked_at))
    transitions: List[Dict[str, Any]] = []

    with closing(get_db()) as conn:
        devices = conn.execute(
            "SELECT id, org_id, hostname, last_seen FROM remote_devices"
        ).fetchall()
        statuses = {
            row["device_id"]: bool(row["is_online"])
            for row in conn.execute(
                "SELECT device_id, is_online FROM device_status"
            ).fetchall()
        }

        for device in devices:
            is_online = checked_at - device["last_seen"] <= DEVICE_OFFLINE_AFTER_SECONDS
            previous_status = statuses.get(device["id"])

            if previous_status is None:
                conn.execute(
                    """
                    INSERT INTO device_status (device_id, is_online, updated_at)
                    VALUES (?, ?, ?)
                    """,
                    (device["id"], int(is_online), checked_at)
                )
                continue

            if previous_status == is_online:
                continue

            recovered = is_online
            event = {
                "id": f"dev_{uuid.uuid4().hex}",
                "org_id": device["org_id"],
                "device_id": device["id"],
                "key": "device_recovered" if recovered else "device_offline",
                "level": "Ma'lumot" if recovered else "Muhim",
                "title": (
                    f"Qurilma qayta ulandi: {device['hostname']}"
                    if recovered else f"Qurilma offline: {device['hostname']}"
                ),
                "message": (
                    "Qurilmadan telemetriya qayta qabul qilindi."
                    if recovered else
                    f"{DEVICE_OFFLINE_AFTER_SECONDS} soniyadan ko'proq vaqt davomida "
                    "qurilmadan telemetriya kelmadi."
                ),
                "recommendation": (
                    "Qurilma holati normal. Monitoringni davom ettiring."
                    if recovered else
                    "Kompyuter yoqilganini, tarmoq ulanishini va LabPulse agenti "
                    "ishlayotganini tekshiring."
                ),
                "timestamp": timestamp,
                "acknowledged": False,
            }
            conn.execute(
                """
                INSERT INTO device_status_events (
                    id, org_id, device_id, key, level, title, message,
                    recommendation, timestamp, acknowledged
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    event["id"], event["org_id"], event["device_id"],
                    event["key"], event["level"], event["title"],
                    event["message"], event["recommendation"], timestamp
                )
            )
            conn.execute(
                """
                UPDATE device_status
                SET is_online = ?, updated_at = ?
                WHERE device_id = ?
                """,
                (int(is_online), checked_at, device["id"])
            )
            transitions.append(event)

        conn.execute(
            """
            DELETE FROM device_status_events
            WHERE id NOT IN (
                SELECT id FROM device_status_events
                ORDER BY timestamp DESC, rowid DESC
                LIMIT ?
            )
            """,
            (MAX_DEVICE_STATUS_EVENTS,)
        )
        conn.commit()

    return transitions


def get_device_status_alerts() -> List[Dict[str, Any]]:
    """Qurilma holati bo'yicha saqlangan ogohlantirishlarni qaytaradi."""
    with closing(get_db()) as conn:
        rows = conn.execute(
            """
            SELECT id, org_id, device_id, key, level, title, message,
                   recommendation, timestamp, acknowledged
            FROM device_status_events
            ORDER BY timestamp DESC, rowid DESC
            """
        ).fetchall()
    events = [dict(row) for row in rows]
    for event in events:
        event["acknowledged"] = bool(event["acknowledged"])
    return events


def acknowledge_device_status_alert(alert_id: str) -> bool:
    """Saqlangan qurilma ogohlantirishini ko'rib chiqilgan deb belgilaydi."""
    with closing(get_db()) as conn:
        cursor = conn.execute(
            "UPDATE device_status_events SET acknowledged = 1 WHERE id = ?",
            (alert_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
