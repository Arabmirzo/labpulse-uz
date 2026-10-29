# app/services/system_metrics.py
"""
Lokal tizim metrikalari — psutil orqali.
"""
import platform
import socket
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List

import psutil

# Bounded history: last 120 samples
_history: Deque[Dict[str, Any]] = deque(maxlen=120)

# CPU warm-up: first psutil.cpu_percent call with interval=None returns 0.0
# We call it once at import time to initialise the counters.
psutil.cpu_percent(interval=None)


def _get_disk() -> Dict[str, Any]:
    """Return disk usage for the primary drive."""
    try:
        if platform.system() == "Windows":
            path = "C:\\"
        else:
            path = "/"
        usage = psutil.disk_usage(path)
        return {
            "path": path,
            "used_percent": round(usage.percent, 1),
            "total_bytes": usage.total,
            "free_bytes": usage.free,
            "used_bytes": usage.used,
        }
    except Exception as exc:
        return {"error": str(exc), "used_percent": None, "total_bytes": 0, "free_bytes": 0}


def _get_uptime() -> float:
    try:
        return time.time() - psutil.boot_time()
    except Exception:
        return 0.0


def collect_metrics() -> Dict[str, Any]:
    """Collect a single snapshot of local machine metrics."""
    try:
        cpu = psutil.cpu_percent(interval=None)
    except Exception:
        cpu = None

    try:
        mem = psutil.virtual_memory()
        memory = {
            "used_percent": round(mem.percent, 1),
            "total_bytes": mem.total,
            "available_bytes": mem.available,
            "used_bytes": mem.used,
        }
    except Exception as exc:
        memory = {"error": str(exc), "used_percent": None}

    disk = _get_disk()

    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = "noma'lum"

    snapshot: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hostname": hostname,
        "platform": platform.system(),
        "platform_version": platform.version(),
        "cpu_percent": cpu,
        "cpu_count": psutil.cpu_count(logical=True),
        "memory": memory,
        "disk": disk,
        "uptime_seconds": round(_get_uptime()),
        "data_source": "local",
    }

    _history.append({
        "timestamp": snapshot["timestamp"],
        "cpu_percent": cpu,
        "memory_percent": memory.get("used_percent"),
    })

    return snapshot


def get_history() -> List[Dict[str, Any]]:
    """Return the bounded metrics history list."""
    return list(_history)


def format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days} kun")
    if hours:
        parts.append(f"{hours} soat")
    if minutes or not parts:
        parts.append(f"{minutes} daqiqa")
    return " ".join(parts)
