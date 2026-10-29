"""
LabPulse UZ — Firebase Realtime Sync Xizmati.
Har bir masofaviy kompyuter telemetriyasini real-vaqtda Firebase'ga sinxronizatsiya qiladi.
"""
import os
import httpx
from typing import Any, Dict
from app.config import get_settings


async def sync_device_to_firebase(org_id: str, device_data: Dict[str, Any]) -> bool:
    """
    Qurilma telemetriyasini Firebase Realtime Database'ga uzatish.
    Agar Firebase sozlanmagan bo'lsa, xatosiz chetlab o'tadi.
    """
    settings = get_settings()
    fb_url = settings.get("firebase_db_url") or os.environ.get("FIREBASE_DB_URL")
    fb_secret = settings.get("firebase_secret") or os.environ.get("FIREBASE_SECRET")

    if not fb_url:
        return False

    fb_url = fb_url.rstrip("/")
    device_id = device_data.get("id") or device_data.get("device_id")

    # Firebase REST Endpoint: /organizations/{org_id}/devices/{device_id}.json
    endpoint = f"{fb_url}/organizations/{org_id}/devices/{device_id}.json"
    if fb_secret:
        endpoint += f"?auth={fb_secret}"

    payload = {
        "id": device_id,
        "org_id": org_id,
        "hostname": device_data.get("hostname"),
        "platform": device_data.get("platform"),
        "ip_address": device_data.get("ip_address"),
        "cpu_percent": device_data.get("cpu_percent"),
        "memory": device_data.get("memory"),
        "disk": device_data.get("disk"),
        "uptime_seconds": device_data.get("uptime_seconds"),
        "is_online": device_data.get("is_online", True),
        "last_seen": device_data.get("last_seen"),
        "last_seen_formatted": device_data.get("last_seen_formatted")
    }

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.put(endpoint, json=payload)
            return resp.status_code in (200, 204)
    except Exception as exc:
        print(f"[Firebase Sync] Xatolik: {exc}")
        return False
