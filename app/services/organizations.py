"""
LabPulse UZ — Tashkilotlar (Multi-Tenancy) va Masofaviy Qurilmalar Boshqaruvi.
SQLite orqali doimiy saqlash (persisted storage).
"""
import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).parent.parent / "labpulse.db"
DEVICE_OFFLINE_AFTER_SECONDS = 35


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Baza jadvallarini yaratish va dastlabki namunaviy kompaniyani kiritish."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                api_key TEXT UNIQUE NOT NULL,
                contact_email TEXT,
                plan TEXT DEFAULT 'Standard',
                status TEXT DEFAULT 'Faol',
                created_at TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS remote_devices (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                hostname TEXT NOT NULL,
                platform TEXT,
                ip_address TEXT,
                cpu_percent REAL,
                memory_json TEXT,
                disk_json TEXT,
                uptime_seconds INTEGER,
                last_seen REAL NOT NULL,
                history_json TEXT,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS device_status (
                device_id TEXT PRIMARY KEY,
                is_online INTEGER NOT NULL,
                updated_at REAL NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS device_status_events (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                device_id TEXT NOT NULL,
                key TEXT NOT NULL,
                level TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                acknowledged INTEGER NOT NULL DEFAULT 0
            );
        """)

        # Standart namunaviy kompaniya (demo / sinov uchun)
        cur = conn.execute("SELECT COUNT(*) as cnt FROM organizations")
        if cur.fetchone()["cnt"] == 0:
            now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            conn.execute("""
                INSERT INTO organizations (id, name, api_key, contact_email, plan, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "org_demo",
                "Demo IT Akademiya (Namuna)",
                "lp_live_demo12345",
                "admin@it-academy.uz",
                "Enterprise",
                "Faol",
                now_iso
            ))
        conn.commit()


# Baza ishga tushiriladi
init_db()


# ------------------------------------------------------------------
# Tashkilotlar (Organizations) funksiyalari
# ------------------------------------------------------------------
def list_organizations() -> List[Dict[str, Any]]:
    """Barcha tashkilotlar va ularning kompyuterlar soni."""
    with get_db() as conn:
        cur = conn.execute("SELECT * FROM organizations ORDER BY created_at DESC")
        rows = [dict(r) for r in cur.fetchall()]

    # Har bir tashkilot uchun ulangan qurilmalar sonini hisoblash
    for org in rows:
        devs = get_devices_by_org(org["id"])
        org["total_devices"] = len(devs)
        org["online_devices"] = len([d for d in devs if d["is_online"]])
        org["offline_devices"] = org["total_devices"] - org["online_devices"]
    return rows


def get_organization_by_key(api_key: str) -> Optional[Dict[str, Any]]:
    """API Kalit bo'yicha tashkilotni topish."""
    with get_db() as conn:
        cur = conn.execute("SELECT * FROM organizations WHERE api_key = ?", (api_key.strip(),))
        row = cur.fetchone()
        return dict(row) if row else None


def get_organization_by_id(org_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cur = conn.execute("SELECT * FROM organizations WHERE id = ?", (org_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_organization(name: str, contact_email: str = "", plan: str = "Standard") -> Dict[str, Any]:
    """Yangi kompaniya qo'shish va unga unikal API kalit yaratish."""
    org_id = f"org_{uuid.uuid4().hex[:8]}"
    api_key = f"lp_live_{uuid.uuid4().hex[:16]}"
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    with get_db() as conn:
        conn.execute("""
            INSERT INTO organizations (id, name, api_key, contact_email, plan, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (org_id, name, api_key, contact_email, plan, "Faol", now_iso))
        conn.commit()

    return {
        "id": org_id,
        "name": name,
        "api_key": api_key,
        "contact_email": contact_email,
        "plan": plan,
        "status": "Faol",
        "created_at": now_iso
    }


def delete_organization(org_id: str) -> bool:
    with get_db() as conn:
        device_ids = [
            row["id"]
            for row in conn.execute(
                "SELECT id FROM remote_devices WHERE org_id = ?", (org_id,)
            ).fetchall()
        ]
        if device_ids:
            placeholders = ",".join("?" for _ in device_ids)
            conn.execute(
                f"DELETE FROM device_status_events WHERE device_id IN ({placeholders})",
                device_ids
            )
            conn.execute(
                f"DELETE FROM device_status WHERE device_id IN ({placeholders})",
                device_ids
            )
        conn.execute("DELETE FROM remote_devices WHERE org_id = ?", (org_id,))
        cur = conn.execute("DELETE FROM organizations WHERE id = ?", (org_id,))
        conn.commit()
        return cur.rowcount > 0


# ------------------------------------------------------------------
# Masofaviy Qurilmalar (Remote Devices) funksiyalari
# ------------------------------------------------------------------
def record_device_telemetry(org_id: str, payload: Dict[str, Any], client_ip: str = "") -> Dict[str, Any]:
    """
    Masofaviy agentdan kelgan jonli telemetriyani saqlash va yangilash.
    """
    device_id = payload.get("device_id")
    if not device_id:
        # Hostname asosida hosil qilamiz
        device_id = f"dev_{payload.get('hostname', 'unknown').lower().replace(' ', '_')}"

    now = time.time()
    hostname = payload.get("hostname", device_id)
    platform_name = payload.get("platform", "Windows")
    ip_addr = payload.get("ip_address") or client_ip
    cpu_percent = float(payload.get("cpu_percent") or 0.0)
    memory_dict = payload.get("memory", {})
    disk_dict = payload.get("disk", {})
    uptime_sec = int(payload.get("uptime_seconds") or 0)

    # Mavjud tarixni olish va yangi nuqta qo'shish
    existing = get_device_by_id(device_id)
    history = []
    if existing and existing.get("history"):
        history = existing.get("history")
    history.append({
        "timestamp": time.strftime("%H:%M:%S", time.localtime()),
        "cpu_percent": cpu_percent,
        "memory_percent": memory_dict.get("used_percent", 0)
    })
    if len(history) > 60:
        history.pop(0)

    with get_db() as conn:
        conn.execute("""
            INSERT INTO remote_devices (id, org_id, hostname, platform, ip_address, cpu_percent, memory_json, disk_json, uptime_seconds, last_seen, history_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                org_id = excluded.org_id,
                hostname = excluded.hostname,
                platform = excluded.platform,
                ip_address = excluded.ip_address,
                cpu_percent = excluded.cpu_percent,
                memory_json = excluded.memory_json,
                disk_json = excluded.disk_json,
                uptime_seconds = excluded.uptime_seconds,
                last_seen = excluded.last_seen,
                history_json = excluded.history_json
        """, (
            device_id,
            org_id,
            hostname,
            platform_name,
            ip_addr,
            cpu_percent,
            json.dumps(memory_dict),
            json.dumps(disk_dict),
            uptime_sec,
            now,
            json.dumps(history)
        ))
        conn.commit()

    return get_device_by_id(device_id)


def get_device_by_id(device_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cur = conn.execute("SELECT * FROM remote_devices WHERE id = ?", (device_id,))
        row = cur.fetchone()
        if not row:
            return None
        return _parse_device_row(dict(row))


def get_devices_by_org(org_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Barcha yoki ko'rsatilgan tashkilot qurilmalari."""
    with get_db() as conn:
        if org_id:
            cur = conn.execute("SELECT * FROM remote_devices WHERE org_id = ? ORDER BY hostname ASC", (org_id,))
        else:
            cur = conn.execute("SELECT * FROM remote_devices ORDER BY hostname ASC")
        rows = [dict(r) for r in cur.fetchall()]

    return [_parse_device_row(r) for r in rows]


def delete_device(device_id: str) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM device_status_events WHERE device_id = ?", (device_id,))
        conn.execute("DELETE FROM device_status WHERE device_id = ?", (device_id,))
        cur = conn.execute("DELETE FROM remote_devices WHERE id = ?", (device_id,))
        conn.commit()
        return cur.rowcount > 0


def manual_register_device(
    org_id: str,
    hostname: str,
    ip_address: str,
    platform_name: str = "Windows 11 Pro",
    device_id: Optional[str] = None
) -> Dict[str, Any]:
    """Admin paneldan kompyuterni qo'lda ro'yxatdan o'tkazish."""
    if not device_id:
        clean_name = "".join(c for c in hostname if c.isalnum() or c in "-_").lower()
        if not clean_name:
            clean_name = "pc"
        device_id = f"pc_{clean_name}_{uuid.uuid4().hex[:4]}"

    now = time.time()
    memory_dict = {"used_percent": 0.0, "total_bytes": 16 * 1024**3, "used_bytes": 0}
    disk_dict = {"used_percent": 0.0, "total_bytes": 512 * 1024**3, "free_bytes": 512 * 1024**3}

    with get_db() as conn:
        conn.execute("""
            INSERT INTO remote_devices (id, org_id, hostname, platform, ip_address, cpu_percent, memory_json, disk_json, uptime_seconds, last_seen, history_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            device_id,
            org_id,
            hostname,
            platform_name,
            ip_address,
            0.0,
            json.dumps(memory_dict),
            json.dumps(disk_dict),
            0,
            now,
            json.dumps([])
        ))
        conn.commit()

    return get_device_by_id(device_id)


def _parse_device_row(d: Dict[str, Any]) -> Dict[str, Any]:
    now = time.time()
    last_seen = d.get("last_seen", 0)
    # 35 soniyadan beri signal kelmasa -> Offline
    diff_sec = now - last_seen
    is_online = diff_sec <= DEVICE_OFFLINE_AFTER_SECONDS

    memory = {}
    try:
        memory = json.loads(d.get("memory_json") or "{}")
    except Exception:
        pass

    disk = {}
    try:
        disk = json.loads(d.get("disk_json") or "{}")
    except Exception:
        pass

    history = []
    try:
        history = json.loads(d.get("history_json") or "[]")
    except Exception:
        pass

    d["is_online"] = is_online
    d["status_text"] = "Online" if is_online else "Offline"
    d["status_class"] = "badge-success" if is_online else "badge-critical"
    d["memory"] = memory
    d["disk"] = disk
    d["history"] = history
    d["last_seen_formatted"] = time.strftime("%H:%M:%S", time.localtime(last_seen))
    return d
