"""
LabPulse UZ — Masofaviy Kompyuter Agent Dasturi (Remote Monitoring Agent).
Har qanday Windows kompyuteriga o'rnatiladi va uning telemetriyasini markaziy serverga yuboradi.
"""
import argparse
import json
import os
import platform
import socket
import sys
import time
import urllib.request
import urllib.error

# psutil tekshirish
try:
    import psutil
except ImportError:
    print("[Agent] psutil kutubxonasi o'rnatilmoqda...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
    import psutil

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_config.json")


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"[Agent] Konfiguratsiyani saqlashda xatolik: {e}")


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_metrics_snapshot():
    # CPU
    cpu = psutil.cpu_percent(interval=0.5)

    # Memory
    mem = psutil.virtual_memory()
    memory_data = {
        "used_percent": round(mem.percent, 1),
        "total_bytes": mem.total,
        "available_bytes": mem.available,
        "used_bytes": mem.used,
    }

    # Disk
    drive = "C:\\" if platform.system() == "Windows" else "/"
    try:
        d = psutil.disk_usage(drive)
        disk_data = {
            "used_percent": round(d.percent, 1),
            "total_bytes": d.total,
            "free_bytes": d.free,
            "used_bytes": d.used,
        }
    except Exception:
        disk_data = {"used_percent": 0, "total_bytes": 0, "free_bytes": 0}

    uptime = int(time.time() - psutil.boot_time())

    return {
        "hostname": socket.gethostname(),
        "platform": f"{platform.system()} {platform.release()}",
        "ip_address": get_local_ip(),
        "cpu_percent": cpu,
        "memory": memory_data,
        "disk": disk_data,
        "uptime_seconds": uptime,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }


def send_heartbeat(server_url: str, api_key: str, device_id: str, custom_name: str = None) -> bool:
    endpoint = f"{server_url.rstrip('/')}/api/v1/agent/heartbeat"
    data = get_metrics_snapshot()
    if device_id:
        data["device_id"] = device_id
    if custom_name:
        data["hostname"] = custom_name

    json_bytes = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(endpoint, data=json_bytes, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-LabPulse-Key", api_key)

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                return True
    except urllib.error.HTTPError as e:
        print(f"[Agent] Xatolik HTTP {e.code}: {e.reason}")
    except Exception as e:
        print(f"[Agent] Serverga ulanish xatoligi: {e}")
    return False


def main():
    parser = argparse.ArgumentParser(description="LabPulse UZ Monitoring Agenti")
    parser.add_argument("--server", help="Server URL (masalan: http://127.0.0.1:8000)")
    parser.add_argument("--key", help="Tashkilot API Kaliti")
    parser.add_argument("--id", help="Qurilma identifikatori (masalan: PC-01)")
    parser.add_argument("--name", help="Qurilma ko'rinadigan nomi")
    parser.add_argument("--interval", type=int, default=5, help="Yuborish oralig'i (soniya)")

    args = parser.parse_args()
    cfg = load_config()

    server_url = args.server or cfg.get("server_url") or "http://127.0.0.1:8000"
    api_key = args.key or cfg.get("api_key")
    device_id = args.id or cfg.get("device_id") or socket.gethostname()
    custom_name = args.name or cfg.get("custom_name") or socket.gethostname()
    interval = args.interval or cfg.get("interval", 5)

    if not api_key:
        print("==================================================")
        print("       LabPulse UZ — Agentni Sozlash")
        print("==================================================")
        server_url = input(f"Server manzili [{server_url}]: ").strip() or server_url
        api_key = input("Tashkilot API Kalitini kiriting (Admin paneldan oling): ").strip()
        device_id = input(f"Ushbu kompyuter ID raqami [{socket.gethostname()}]: ").strip() or socket.gethostname()
        custom_name = input(f"Kompyuter nomi [{device_id}]: ").strip() or device_id

        cfg = {
            "server_url": server_url,
            "api_key": api_key,
            "device_id": device_id,
            "custom_name": custom_name,
            "interval": interval
        }
        save_config(cfg)
        print("\nSozlamalar saqlandi! Monitoring boshlanmoqda...\n")

    print(f"[*] LabPulse UZ Agenti faol ishga tushdi:")
    print(f"    Server:    {server_url}")
    print(f"    Qurilma:   {custom_name} (ID: {device_id})")
    print(f"    Oraliq:    {interval} soniya")
    print("--------------------------------------------------")

    while True:
        success = send_heartbeat(server_url, api_key, device_id, custom_name)
        if success:
            sys.stdout.write(f"\r[OK] Signal yuborildi: {time.strftime('%H:%M:%S')} (CPU: {psutil.cpu_percent()}%) ")
            sys.stdout.flush()
        else:
            sys.stdout.write(f"\r[!] Qayta urinish: {time.strftime('%H:%M:%S')} (Server javob bermadi) ")
            sys.stdout.flush()
        time.sleep(interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Agent] To'xtatildi.")
