# LabPulse UZ — Konfiguratsiya moduli
import os
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).parent.parent

# ------------------------------------------------------------------
# Default settings (can be overridden at runtime via /api/settings)
# ------------------------------------------------------------------
DEFAULT_SETTINGS: Dict[str, Any] = {
    "refresh_interval": 5,          # seconds
    "theme": "dark",
    "diagnostic_target": "8.8.8.8",
    "firebase_db_url": "",          # https://my-labpulse-default-rtdb.firebaseio.com
    "firebase_secret": "",          # Firebase DB Secret / Auth token
    "thresholds": {
        "cpu_critical": 90,
        "ram_critical": 90,
        "ram_warning": 80,
        "disk_critical": 10,        # free % threshold
        "disk_warning": 20,
    },
    "alert_cooldown_seconds": 120,  # avoid duplicate alerts
    "cpu_sustained_samples": 3,     # consecutive samples before CPU alert
}

# In-memory settings store (persists until server restart)
_settings: Dict[str, Any] = dict(DEFAULT_SETTINGS)
_settings["thresholds"] = dict(DEFAULT_SETTINGS["thresholds"])


def get_settings() -> Dict[str, Any]:
    return _settings


def update_settings(partial: Dict[str, Any]) -> Dict[str, Any]:
    """Merge partial settings update with validation."""
    allowed_top = {
        "refresh_interval", "theme", "diagnostic_target",
        "firebase_db_url", "firebase_secret", "thresholds"
    }
    for key in list(partial.keys()):
        if key not in allowed_top:
            raise ValueError(f"Noma'lum sozlama: {key}")

    if "refresh_interval" in partial:
        val = int(partial["refresh_interval"])
        if val not in (3, 5, 10, 30):
            raise ValueError("Yangilanish intervali 3, 5, 10 yoki 30 soniya bo'lishi kerak.")
        _settings["refresh_interval"] = val

    if "theme" in partial:
        if partial["theme"] not in ("dark", "light"):
            raise ValueError("Tema 'dark' yoki 'light' bo'lishi kerak.")
        _settings["theme"] = partial["theme"]

    if "diagnostic_target" in partial:
        target = str(partial["diagnostic_target"]).strip()
        _validate_hostname(target)
        _settings["diagnostic_target"] = target

    if "firebase_db_url" in partial:
        _settings["firebase_db_url"] = str(partial["firebase_db_url"]).strip()

    if "firebase_secret" in partial:
        _settings["firebase_secret"] = str(partial["firebase_secret"]).strip()

    if "thresholds" in partial:
        th = partial["thresholds"]
        merged = dict(_settings["thresholds"])
        int_keys = {"cpu_critical", "ram_critical", "ram_warning",
                    "disk_critical", "disk_warning"}
        for k, v in th.items():
            if k not in int_keys:
                raise ValueError(f"Noma'lum threshold: {k}")
            iv = int(v)
            if not (0 < iv < 100):
                raise ValueError(f"{k} 1–99 oralig'ida bo'lishi kerak.")
            merged[k] = iv
        _settings["thresholds"] = merged

    return _settings


def _validate_hostname(value: str) -> None:
    import re
    if not value:
        raise ValueError("Diagnostika manzili bo'sh bo'lishi mumkin emas.")
    if len(value) > 253:
        raise ValueError("Manzil juda uzun.")
    ip_re = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")
    host_re = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9\-\.]{0,251}[a-zA-Z0-9])?$")
    if not (ip_re.match(value) or host_re.match(value)):
        raise ValueError("Noto'g'ri hostname yoki IP manzil.")
