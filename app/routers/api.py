"""
LabPulse UZ — Barcha API Endpointlari (Lokal va Multi-Tenant Ingestion).
"""
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Response, Request, Header

from app.services.system_metrics import collect_metrics, get_history
from app.services.network_diagnostics import run_full_network_test, validate_target
from app.services.diagnostic_rules import analyze_metrics, get_system_summary_status
from app.services.alerts import (
    generate_alerts_from_metrics,
    get_alerts,
    acknowledge_alert,
)
from app.services.reports import generate_report, get_report_by_id, list_reports
from app.services.organizations import (
    list_organizations,
    create_organization,
    delete_organization,
    get_organization_by_key,
    record_device_telemetry,
    get_devices_by_org,
    delete_device
)
from app.services.firebase_sync import sync_device_to_firebase
from app.config import get_settings, update_settings

router = APIRouter(prefix="/api", tags=["API"])


# ------------------------------------------------------------------
# 1. Asosiy Telemetriya va Salomatlik
# ------------------------------------------------------------------
@router.get("/health")
def api_health():
    """Ilova holati va asosiy parametrlar."""
    return {
        "status": "healthy",
        "service": "LabPulse UZ",
        "version": "1.1.0-cloud",
        "language": "uz"
    }


@router.get("/metrics")
def api_metrics():
    """Lokal kompyuterning joriy haqiqiy metrikalari."""
    try:
        metrics = collect_metrics()
        generate_alerts_from_metrics(metrics)
        return metrics
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Metrikalarni yig'ishda xatolik: {str(exc)}")


@router.get("/history")
def api_history():
    """CPU va RAM o'lchovlari tarixi."""
    return {
        "history": get_history(),
        "total_points": len(get_history())
    }


# ------------------------------------------------------------------
# 2. Masofaviy Agent Heartbeat (Kompaniya kompyuterlaridan qabul qilish)
# ------------------------------------------------------------------
@router.post("/v1/agent/heartbeat")
async def api_agent_heartbeat(
    request: Request,
    x_labpulse_key: Optional[str] = Header(None)
):
    """
    Masofaviy agentdan jonli telemetriyani qabul qilish.
    X-LabPulse-Key orqali qaysi kompaniyaga tegishliligi aniqlanadi.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Noto'g'ri JSON formati.")

    api_key = x_labpulse_key or payload.get("api_key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API Kalit (X-LabPulse-Key) ko'rsatilmadi.")

    org = get_organization_by_key(api_key)
    if not org:
        raise HTTPException(status_code=403, detail="Tashkilot API Kaliti noto'g'ri yoki faol emas.")

    client_ip = request.client.host if request.client else "127.0.0.1"

    # Ma'lumotlar bazasiga yozish
    device = record_device_telemetry(org["id"], payload, client_ip)

    # Agar Firebase yoqilgan bo'lsa, Firebase'ga ham jo'natish
    try:
        await sync_device_to_firebase(org["id"], device)
    except Exception:
        pass

    # Ogohlantirishlarni tekshirish
    generate_alerts_from_metrics({
        "cpu_percent": device.get("cpu_percent"),
        "memory": device.get("memory"),
        "disk": device.get("disk")
    })

    return {
        "status": "ok",
        "ack": True,
        "org_name": org["name"],
        "device_id": device["id"],
        "interval_seconds": 5
    }


# ------------------------------------------------------------------
# 3. Tashkilotlar (Kompaniyalar) Boshqaruvi
# ------------------------------------------------------------------
@router.get("/v1/organizations")
def api_list_organizations():
    """Barcha ro'yxatdan o'tgan kompaniyalar."""
    return {"organizations": list_organizations()}


@router.post("/v1/organizations")
async def api_create_organization(request: Request):
    """Yangi mijoz kompaniyani qo'shish va API Kalit berish."""
    try:
        data = await request.json()
        name = str(data.get("name", "")).strip()
        if not name:
            raise ValueError("Kompaniya nomi bo'sh bo'lishi mumkin emas.")
        email = str(data.get("contact_email", "")).strip()
        plan = str(data.get("plan", "Standard")).strip()

        org = create_organization(name=name, contact_email=email, plan=plan)
        return {"status": "success", "organization": org}
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Tashkilot yaratishda xatolik: {str(exc)}")


@router.delete("/v1/organizations/{org_id}")
def api_delete_organization(org_id: str):
    """Kompaniyani va uning kompyuterlarini o'chirish."""
    success = delete_organization(org_id)
    if not success:
        raise HTTPException(status_code=404, detail="Kompaniya topilmadi.")
    return {"status": "success", "message": "Kompaniya o'chirildi."}


# ------------------------------------------------------------------
# 4. Qurilmalar Ro'yxati (Kompaniya bo'yicha)
# ------------------------------------------------------------------
@router.get("/v1/devices")
def api_list_devices(org_id: Optional[str] = None):
    """Barcha yoki ko'rsatilgan tashkilotning kompyuterlari."""
    devs = get_devices_by_org(org_id)
    return {
        "devices": devs,
        "total": len(devs),
        "online_count": len([d for d in devs if d["is_online"]])
    }


@router.delete("/v1/devices/{device_id}")
def api_delete_device(device_id: str):
    success = delete_device(device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Qurilma topilmadi.")
    return {"status": "success", "message": "Qurilma ro'yxatdan o'chirildi."}


@router.post("/v1/devices/manual")
async def api_manual_add_device(request: Request):
    """Admin paneldan kompyuterni qo'lda ro'yxatdan o'tkazish."""
    try:
        data = await request.json()
        org_id = data.get("org_id")
        if not org_id:
            raise ValueError("Kompaniya tanlanmadi.")
        hostname = str(data.get("hostname", "")).strip()
        if not hostname:
            raise ValueError("Kompyuter nomi kiritilmadi.")
        ip_addr = str(data.get("ip_address", "192.168.1.1")).strip()
        platform_name = str(data.get("platform", "Windows 11 Pro")).strip()
        custom_id = str(data.get("device_id", "")).strip() or None

        from app.services.organizations import manual_register_device
        device = manual_register_device(org_id, hostname, ip_addr, platform_name, custom_id)
        return {"status": "success", "device": device}
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Kompyuterni qo'shishda xatolik: {str(exc)}")


@router.get("/v1/agent/installer-script")
def api_download_agent_installer(request: Request, org_id: str):
    """
    Ushbu kompaniya uchun avtomatik sozlangan 1-klikli install_agent.bat skriptini yuklab olish.
    """
    from app.services.organizations import get_organization_by_id
    org = get_organization_by_id(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Kompaniya topilmadi.")

    # Server URL ni joriy so'rovdan aniqlash
    host = request.headers.get("host", "127.0.0.1:8000")
    protocol = "https" if request.url.scheme == "https" else "http"
    server_url = f"{protocol}://{host}"
    api_key = org["api_key"]

    script_content = f"""@echo off
chcp 65001 > nul
title LabPulse UZ Agent — {org['name']}
echo ============================================================
echo   LabPulse UZ — {org['name']} uchun Agent
echo   Server: {server_url}
echo ============================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [XATO] Ushbu kompyuterda Python topilmadi!
    echo Iltimos, avval Python o'rnating: https://www.python.org/downloads/
    pause
    exit /b 1
)

python -m pip install psutil >nul 2>nul

:: Agent konfiguratsiyasini avtomatik yaratish
(
echo {{
echo   "server_url": "{server_url}",
echo   "api_key": "{api_key}",
echo   "interval": 5
echo }}
) > "%~dp0agent_config.json"

echo [OK] Konfiguratsiya saqlandi!
echo Kompyuter avtomatik ravishda {org['name']} kabinetiga ulandi!
echo.
python "%~dp0labpulse_agent.py"
pause
"""
    filename = f"labpulse_installer_{org_id}.bat"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=script_content, media_type="application/octet-stream", headers=headers)



# ------------------------------------------------------------------
# 5. Diagnostika, Alertlar va Hisobotlar
# ------------------------------------------------------------------
@router.post("/diagnostics/run")
async def api_run_diagnostics(request: Request):
    try:
        body = {}
        try:
            body = await request.json()
        except Exception:
            pass

        settings = get_settings()
        target = body.get("target") or settings.get("diagnostic_target", "8.8.8.8")
        clean_target = validate_target(target)

        metrics = collect_metrics()
        network = run_full_network_test(ping_target=clean_target)
        findings = analyze_metrics(metrics, network)
        summary = get_system_summary_status(findings)
        generate_alerts_from_metrics(metrics, network)

        return {
            "target": clean_target,
            "summary": summary,
            "metrics": metrics,
            "network": network,
            "findings": findings
        }
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Diagnostika xatoligi: {str(exc)}")


@router.get("/alerts")
def api_get_alerts(only_unacknowledged: bool = False):
    alerts = get_alerts(only_unacknowledged=only_unacknowledged)
    return {
        "alerts": alerts,
        "total": len(alerts),
        "unacknowledged_count": len([a for a in alerts if not a.get("acknowledged")])
    }


@router.post("/alerts/{alert_id}/acknowledge")
def api_acknowledge_alert(alert_id: str):
    success = acknowledge_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ko'rsatilgan ID dagi ogohlantirish topilmadi.")
    return {"status": "success", "alert_id": alert_id, "message": "Ogohlantirish ko'rib chiqildi deb belgilandi."}


@router.post("/reports")
async def api_create_report(request: Request):
    note = ""
    try:
        body = await request.json()
        note = body.get("note", "")
    except Exception:
        pass
    report = generate_report(custom_note=note)
    return report


@router.get("/reports")
def api_list_reports():
    return {"reports": list_reports()}


@router.get("/reports/{report_id}/download")
def api_download_report(report_id: str):
    rep = get_report_by_id(report_id)
    if not rep:
        raise HTTPException(status_code=404, detail="Hisobot topilmadi.")

    content = json.dumps(rep, indent=2, ensure_ascii=False)
    filename = f"labpulse_hisobot_{report_id}.json"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=content, media_type="application/json", headers=headers)


@router.get("/settings")
def api_get_settings():
    return get_settings()


@router.put("/settings")
async def api_update_settings(request: Request):
    try:
        data = await request.json()
        updated = update_settings(data)
        return {"status": "success", "settings": updated}
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Sozlamalarni saqlashda xatolik: {str(exc)}")
