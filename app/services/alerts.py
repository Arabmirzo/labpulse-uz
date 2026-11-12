"""
Ogohlantirishlar (Alerts) xizmati:
- Qoidalar bo'yicha ogohlantirishlarni shakllantirish
- Debounce / cooldown mexanizmi (bir xil alert qayta-qayta toshib ketmasligi uchun)
- CPU sustained samples hisobi
- Alertni 'ko'rib chiqildi' (acknowledged) deb belgilash
"""
import time
import uuid
from typing import Any, Dict, List, Optional
from app.config import get_settings
from app.services.device_monitoring import (
    acknowledge_device_status_alert,
    get_device_status_alerts,
)

# Alertlar xotirada saqlanadi
_alerts: List[Dict[str, Any]] = []

# Cooldown va sustained CPU monitoring holati
_last_fired_times: Dict[str, float] = {}
_consecutive_high_cpu_count = 0


def generate_alerts_from_metrics(metrics: Dict[str, Any], network_results: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Joriy o'lchovlar va tarmoq testidan yangi alertlarni tekshiradi va qo'shadi.
    """
    global _consecutive_high_cpu_count
    settings = get_settings()
    th = settings.get("thresholds", {})
    cooldown = settings.get("alert_cooldown_seconds", 120)
    sustained_cpu_target = settings.get("cpu_sustained_samples", 3)

    cpu_crit = th.get("cpu_critical", 90)
    ram_crit = th.get("ram_critical", 90)
    ram_warn = th.get("ram_warning", 80)
    disk_crit = th.get("disk_critical", 10)
    disk_warn = th.get("disk_warning", 20)

    now = time.time()
    iso_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    new_alerts: List[Dict[str, Any]] = []

    def _should_fire(key: str) -> bool:
        last = _last_fired_times.get(key, 0)
        return (now - last) >= cooldown

    def _record_alert(alert_key: str, level: str, title: str, message: str, recommendation: str):
        _last_fired_times[alert_key] = now
        alert_obj = {
            "id": str(uuid.uuid4())[:8],
            "key": alert_key,
            "level": level,  # "Ma'lumot", "Diqqat", "Muhim"
            "title": title,
            "message": message,
            "recommendation": recommendation,
            "timestamp": iso_time,
            "acknowledged": False
        }
        _alerts.insert(0, alert_obj)
        # 100 ta alertdan oshsa eskilarini kesib tashlaymiz
        if len(_alerts) > 100:
            _alerts.pop()
        new_alerts.append(alert_obj)

    # 1. Sustained CPU
    cpu_val = metrics.get("cpu_percent")
    if cpu_val is not None:
        if cpu_val >= cpu_crit:
            _consecutive_high_cpu_count += 1
            if _consecutive_high_cpu_count >= sustained_cpu_target and _should_fire("cpu_critical"):
                _record_alert(
                    "cpu_critical",
                    "Muhim",
                    f"CPU doimiy yuqori yuklanishda ({cpu_val}%)",
                    f"Protsessor oxirgi {_consecutive_high_cpu_count} ta o'lchovda {cpu_crit}% dan yuqori bo'ldi.",
                    "Ortiqcha dasturlarni yoping yoki tizimni qayta ishga tushiring."
                )
        else:
            _consecutive_high_cpu_count = 0

    # 2. RAM
    mem = metrics.get("memory", {})
    ram_val = mem.get("used_percent")
    if ram_val is not None:
        if ram_val >= ram_crit and _should_fire("ram_critical"):
            _record_alert(
                "ram_critical",
                "Muhim",
                f"RAM kritik darajada to'ldi ({ram_val}%)",
                f"Operativ xotira {ram_crit}% chegarasidan oshdi.",
                "Brauzer varaqlari va katta xotira talab qiluvchi dasturlarni yoping."
            )
        elif ram_val >= ram_warn and _should_fire("ram_warning"):
            _record_alert(
                "ram_warning",
                "Diqqat",
                f"RAM to'lib bormoqda ({ram_val}%)",
                f"Operativ xotira {ram_warn}% chegarasidan oshdi.",
                "Foydalanilmayotgan dasturlarni yakunlash tavsiya etiladi."
            )

    # 3. Disk
    disk = metrics.get("disk", {})
    total_b = disk.get("total_bytes", 0)
    free_b = disk.get("free_bytes", 0)
    if total_b > 0:
        free_p = round((free_b / total_b * 100), 1)
        if free_p <= disk_crit and _should_fire("disk_critical"):
            _record_alert(
                "disk_critical",
                "Muhim",
                f"Diskda bo'sh joy kritik darajada kam ({free_p}%)",
                f"Asosiy diskda faqat {free_p}% bo'sh joy qoldi.",
                "Diskni zudlik bilan keraksiz fayllardan tozalang."
            )
        elif free_p <= disk_warn and _should_fire("disk_warning"):
            _record_alert(
                "disk_warning",
                "Diqqat",
                f"Disk to'lib bormoqda ({free_p}% qoldi)",
                f"Disk bo'sh joyi {disk_warn}% dan kam.",
                "Katta hajmdagi vaqtinchalik fayllarni o'chiring."
            )

    # 4. Tarmoq (agar test qilingan bo'lsa)
    if network_results:
        dns_res = network_results.get("dns", {})
        ping_res = network_results.get("ping", {})

        if dns_res.get("status") != "success" and _should_fire("dns_failed"):
            _record_alert(
                "dns_failed",
                "Diqqat",
                "DNS tekshiruvi muvaffaqiyatsiz bo'ldi",
                f"Domen nomini aniqlash imkoni bo'lmadi: {dns_res.get('message')}",
                "DNS sozlamalarini va internet aloqasini tekshiring."
            )

        if ping_res.get("status") != "success" and _should_fire("ping_failed"):
            _record_alert(
                "ping_failed",
                "Diqqat",
                f"Tarmoqqa ulanish yo'q ({ping_res.get('target')})",
                f"Ping javob bermadi: {ping_res.get('message')}",
                "Kabel yoki router ulanishini ko'zdan kechiring."
            )

    return new_alerts


def get_alerts(only_unacknowledged: bool = False) -> List[Dict[str, Any]]:
    """Mavjud alertlar ro'yxatini qaytarish."""
    alerts = list(_alerts) + get_device_status_alerts()
    if only_unacknowledged:
        alerts = [a for a in alerts if not a.get("acknowledged")]
    return sorted(alerts, key=lambda alert: alert.get("timestamp", ""), reverse=True)


def acknowledge_alert(alert_id: str) -> bool:
    """Alertni ko'rib chiqilgan deb belgilash."""
    for alert in _alerts:
        if alert.get("id") == alert_id:
            alert["acknowledged"] = True
            return True
    return acknowledge_device_status_alert(alert_id)


def clear_all_alerts() -> None:
    """Alertlarni tozalash (testlar uchun)."""
    global _consecutive_high_cpu_count
    _alerts.clear()
    _last_fired_times.clear()
    _consecutive_high_cpu_count = 0
