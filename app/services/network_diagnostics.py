"""
Tarmoq diagnostikasi xizmati:
- DNS lookup (socket.getaddrinfo)
- Ping / ulanish testi (xavfsiz subprocess, timeout, argumentlar ro'yxati)
"""
import platform
import re
import socket
import subprocess
import time
from typing import Any, Dict


def validate_target(target: str) -> str:
    """Tekshirish manzilini xavfsiz formatga tekshirish."""
    if not target or not isinstance(target, str):
        raise ValueError("Diagnostika manzili ko'rsatilmadi.")
    target = target.strip()
    if len(target) > 253:
        raise ValueError("Manzil juda uzun.")
    ip_re = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")
    host_re = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9\-\.]{0,251}[a-zA-Z0-9])?$")
    if not (ip_re.match(target) or host_re.match(target)):
        raise ValueError("Noto'g'ri IP yoki host formati.")
    return target


def check_dns(domain: str = "google.com", timeout: float = 3.0) -> Dict[str, Any]:
    """DNS yechimini tekshirish."""
    start = time.perf_counter()
    try:
        domain = validate_target(domain)
        # socket default timeout vaqtinchalik o'rnatiladi
        prev_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout)
        try:
            results = socket.getaddrinfo(domain, 80, socket.AF_INET, socket.SOCK_STREAM)
            elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
            ips = list({res[4][0] for res in results if res and len(res) >= 5})
            return {
                "status": "success",
                "target": domain,
                "latency_ms": elapsed_ms,
                "resolved_ips": ips,
                "message": f"DNS yechimi muvaffaqiyatli: {', '.join(ips[:3])}"
            }
        finally:
            socket.setdefaulttimeout(prev_timeout)
    except socket.gaierror as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        return {
            "status": "failed",
            "target": domain,
            "latency_ms": elapsed_ms,
            "error": "DNS manzilni aniqlab bo'lmadi (gaierror)",
            "message": f"'{domain}' manzili uchun DNS yechimi muvaffaqiyatsiz bo'ldi."
        }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        return {
            "status": "failed",
            "target": domain,
            "latency_ms": elapsed_ms,
            "error": str(exc),
            "message": f"DNS tekshiruvi xatoligi: {str(exc)}"
        }


def check_ping(target: str = "8.8.8.8", timeout: float = 3.0) -> Dict[str, Any]:
    """
    Ping testi — xavfsiz ro'yxat ko'rinishidagi buyruq bilan (shell=False).
    Windows va Linux parametrlarini moslashtiradi.
    """
    try:
        clean_target = validate_target(target)
    except ValueError as val_err:
        return {
            "status": "error",
            "target": target,
            "latency_ms": None,
            "message": str(val_err)
        }

    is_windows = platform.system() == "Windows"
    timeout_ms = int(timeout * 1000)

    if is_windows:
        # ping -n 1 -w 3000 <target>
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), clean_target]
    else:
        # ping -c 1 -W 3 <target>
        cmd = ["ping", "-c", "1", "-W", str(int(timeout)), clean_target]

    start = time.perf_counter()
    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout + 1.0,
            shell=False
        )
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

        if res.returncode == 0:
            # Latency parsing urinishi
            latency = elapsed_ms
            out = res.stdout
            # Windows: time=12ms yoki time<1ms
            m = re.search(r"time[<=](\d+(\.\d+)?)ms", out, re.IGNORECASE)
            if m:
                latency = float(m.group(1))
            else:
                # Linux: time=12.3 ms
                m2 = re.search(r"time=(\d+(\.\d+)?) ms", out, re.IGNORECASE)
                if m2:
                    latency = float(m2.group(1))

            return {
                "status": "success",
                "target": clean_target,
                "latency_ms": latency,
                "message": f"Ulanish mavjud ({latency} ms)"
            }
        else:
            return {
                "status": "failed",
                "target": clean_target,
                "latency_ms": None,
                "message": f"Paket qabul qilinmadi (Ping javob bermadi)"
            }
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "target": clean_target,
            "latency_ms": None,
            "message": f"Kutish vaqti tugadi (Timeout: {timeout}s)"
        }
    except Exception as exc:
        return {
            "status": "error",
            "target": clean_target,
            "latency_ms": None,
            "message": f"Ping bajarishda xatolik: {str(exc)}"
        }


def run_full_network_test(ping_target: str = "8.8.8.8", dns_domain: str = "google.com") -> Dict[str, Any]:
    """To'liq tarmoq diagnostika to'plami."""
    dns_res = check_dns(dns_domain)
    ping_res = check_ping(ping_target)
    
    overall = "success"
    if dns_res["status"] != "success" or ping_res["status"] != "success":
        overall = "warning" if (dns_res["status"] == "success" or ping_res["status"] == "success") else "failed"

    return {
        "overall_status": overall,
        "dns": dns_res,
        "ping": ping_res,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
