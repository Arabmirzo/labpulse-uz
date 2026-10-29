"""
LabPulse UZ — Frontend sahifalar routeri (Jinja2 render).
Multi-Tenancy, Kompaniyalar boshqaruvi va Masofaviy qurilmalar.
"""
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates

from app.services.system_metrics import collect_metrics, format_uptime
from app.services.alerts import get_alerts
from app.services.reports import list_reports, get_report_by_id
from app.services.organizations import (
    list_organizations,
    get_devices_by_org,
    get_device_by_id,
    get_organization_by_id
)
from app.config import get_settings

router = APIRouter(tags=["Pages"])

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/")
def page_dashboard(request: Request):
    """Bosh sahifa: Umumiy ko'rinish va jonli telemetriya."""
    settings = get_settings()
    orgs = list_organizations()
    all_devs = get_devices_by_org()
    total_remote = len(all_devs)
    online_remote = len([d for d in all_devs if d["is_online"]])

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "active_page": "dashboard",
            "settings": settings,
            "page_title": "Umumiy ko'rinish",
            "org_count": len(orgs),
            "total_remote": total_remote,
            "online_remote": online_remote
        }
    )


@router.get("/devices")
def page_devices(request: Request, org_id: str = None):
    """
    Kompyuterlar sahifasi:
    Kompaniyalar bo'yicha ulangan haqiqiy masofaviy kompyuterlar ro'yxati.
    """
    settings = get_settings()
    local_metrics = collect_metrics()
    orgs = list_organizations()

    # Agar org_id ko'rsatilmagan bo'lsa, birinchi tashkilotni yoki barchasini olamiz
    selected_org = None
    if org_id:
        selected_org = get_organization_by_id(org_id)
    elif orgs:
        selected_org = orgs[0]

    remote_devices = get_devices_by_org(selected_org["id"] if selected_org else None)

    # Lokal qurilma
    local_device = {
        "hostname": local_metrics.get("hostname"),
        "platform": f"{local_metrics.get('platform')} {local_metrics.get('platform_version')}",
        "cpu_percent": local_metrics.get("cpu_percent"),
        "ram_percent": local_metrics.get("memory", {}).get("used_percent"),
        "disk_percent": local_metrics.get("disk", {}).get("used_percent"),
        "uptime": format_uptime(local_metrics.get("uptime_seconds", 0)),
        "is_local": True,
        "status": "Faol (Online)",
        "status_class": "badge-success"
    }

    return templates.TemplateResponse(
        request=request,
        name="devices.html",
        context={
            "request": request,
            "active_page": "devices",
            "local_device": local_device,
            "remote_devices": remote_devices,
            "organizations": orgs,
            "selected_org": selected_org,
            "settings": settings,
            "page_title": "Kompyuterlar Boshqaruvi"
        }
    )


@router.get("/devices/{device_id}")
def page_device_detail(request: Request, device_id: str):
    """Tanlangan masofaviy kompyuterning to'liq holati."""
    dev = get_device_by_id(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Qurilma topilmadi.")

    settings = get_settings()
    org = get_organization_by_id(dev["org_id"])

    return templates.TemplateResponse(
        request=request,
        name="device_detail.html",
        context={
            "request": request,
            "active_page": "devices",
            "device": dev,
            "org": org,
            "settings": settings,
            "page_title": f"{dev['hostname']} — Qurilma tafsiloti"
        }
    )


@router.get("/admin/organizations")
def page_admin_organizations(request: Request):
    """Tashkilotlar va mijozlarni boshqarish paneli (B2B SaaS)."""
    settings = get_settings()
    orgs = list_organizations()
    return templates.TemplateResponse(
        request=request,
        name="organizations.html",
        context={
            "request": request,
            "active_page": "organizations",
            "organizations": orgs,
            "settings": settings,
            "page_title": "Tashkilotlar va API Kalitlar"
        }
    )


@router.get("/diagnostics")
def page_diagnostics(request: Request):
    settings = get_settings()
    return templates.TemplateResponse(
        request=request,
        name="diagnostics.html",
        context={
            "active_page": "diagnostics",
            "settings": settings,
            "page_title": "Diagnostika"
        }
    )


@router.get("/alerts")
def page_alerts(request: Request):
    settings = get_settings()
    alerts = get_alerts()
    return templates.TemplateResponse(
        request=request,
        name="alerts.html",
        context={
            "active_page": "alerts",
            "alerts": alerts,
            "settings": settings,
            "page_title": "Ogohlantirishlar"
        }
    )


@router.get("/reports")
def page_reports(request: Request):
    settings = get_settings()
    reports = list_reports()
    return templates.TemplateResponse(
        request=request,
        name="reports.html",
        context={
            "active_page": "reports",
            "reports": reports,
            "settings": settings,
            "page_title": "Hisobotlar"
        }
    )


@router.get("/reports/{report_id}/view")
def page_report_view(request: Request, report_id: str):
    report = get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Hisobot topilmadi.")

    settings = get_settings()
    return templates.TemplateResponse(
        request=request,
        name="report_view.html",
        context={
            "active_page": "reports",
            "report": report,
            "settings": settings,
            "page_title": f"Hisobot #{report_id}"
        }
    )


@router.get("/settings")
def page_settings(request: Request):
    settings = get_settings()
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "active_page": "settings",
            "settings": settings,
            "page_title": "Sozlamalar"
        }
    )
