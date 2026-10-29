"""
Hisobotlar (Reports) xizmati:
- Tizim metrikalari, tarmoq tekshiruvlari va tavsiyalar asosida to'liq hisobot yaratish
- JSON formatida saqlash va yuklab olish imkoniyati
"""
import time
import uuid
from typing import Any, Dict, List, Optional
from app.services.system_metrics import collect_metrics, format_uptime
from app.services.network_diagnostics import run_full_network_test
from app.services.diagnostic_rules import analyze_metrics, get_system_summary_status
from app.services.alerts import get_alerts
from app.config import get_settings

# Yaratilgan hisobotlar xotirada saqlanadi
_reports: Dict[str, Dict[str, Any]] = {}


def generate_report(custom_note: str = "") -> Dict[str, Any]:
    """To'liq diagnostika hisobotini shakllantiradi."""
    settings = get_settings()
    target = settings.get("diagnostic_target", "8.8.8.8")
    
    # 1. Haqiqiy metrikalarni yig'ish
    metrics = collect_metrics()
    
    # 2. Tarmoq diagnostikasi
    network = run_full_network_test(ping_target=target)
    
    # 3. Qoidalar bo'yicha tahlil
    findings = analyze_metrics(metrics, network)
    summary_status = get_system_summary_status(findings)
    
    # 4. Mavjud ogohlantirishlar
    current_alerts = get_alerts()
    
    report_id = str(uuid.uuid4())[:8]
    iso_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    display_time = time.strftime("%d.%m.%Y %H:%M:%S", time.localtime())

    report_data = {
        "id": report_id,
        "created_at": iso_time,
        "display_time": display_time,
        "hostname": metrics.get("hostname", "noma'lum"),
        "platform": f"{metrics.get('platform')} {metrics.get('platform_version')}",
        "uptime_formatted": format_uptime(metrics.get("uptime_seconds", 0)),
        "note": custom_note,
        "summary": summary_status,
        "metrics": {
            "cpu_percent": metrics.get("cpu_percent"),
            "cpu_count": metrics.get("cpu_count"),
            "memory": metrics.get("memory"),
            "disk": metrics.get("disk"),
        },
        "network": network,
        "findings": findings,
        "active_alerts_count": len([a for a in current_alerts if not a.get("acknowledged")]),
        "recent_alerts": current_alerts[:5],
        "generated_by": "LabPulse UZ Monitoring Platformasi"
    }

    _reports[report_id] = report_data
    return report_data


def get_report_by_id(report_id: str) -> Optional[Dict[str, Any]]:
    return _reports.get(report_id)


def list_reports() -> List[Dict[str, Any]]:
    # So'nggi yaratilganlar birinchi
    return sorted(list(_reports.values()), key=lambda r: r.get("created_at", ""), reverse=True)
