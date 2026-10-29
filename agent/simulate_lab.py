"""
LabPulse UZ — Sinf/Ofis Kompyuterlarini Simulyatsiya Qilish.
Bir nechta kompyuter nomidan markaziy serverga jonli ma'lumot jo'natadi.
Taqdimotlar (demo va sotuvlar) uchun ideal vosita!
"""
import time
import random
import urllib.request
import json
import sys

SERVER_URL = "http://127.0.0.1:8000"
API_KEY = "lp_live_demo12345"

COMPUTERS = [
    {"id": "PC-LAB-01", "name": "1-Stol (Talaba)", "platform": "Windows 11 Pro", "ip": "192.168.1.101", "ram_total": 16, "disk_total": 512},
    {"id": "PC-LAB-02", "name": "2-Stol (Talaba)", "platform": "Windows 10 Edu", "ip": "192.168.1.102", "ram_total": 8, "disk_total": 256},
    {"id": "PC-TEACHER", "name": "O'qituvchi Kompyuteri", "platform": "Windows 11 Pro", "ip": "192.168.1.100", "ram_total": 32, "disk_total": 1024},
    {"id": "SRV-LAB", "name": "Mahalliy Fayl Server", "platform": "Ubuntu 22.04 LTS", "ip": "192.168.1.5", "ram_total": 64, "disk_total": 4096},
]


def send_simulated_heartbeat(pc):
    endpoint = f"{SERVER_URL}/api/v1/agent/heartbeat"

    # Dinamik o'zgaruvchan CPU va RAM
    base_cpu = 15 if "Server" in pc["name"] else 40
    cpu = round(min(98.0, max(5.0, base_cpu + random.uniform(-15, 30))), 1)

    ram_used_p = round(random.uniform(45.0, 78.0), 1)
    ram_total_b = pc["ram_total"] * (1024**3)
    ram_used_b = int(ram_total_b * (ram_used_p / 100))

    disk_used_p = round(random.uniform(35.0, 60.0), 1)
    disk_total_b = pc["disk_total"] * (1024**3)
    disk_free_b = int(disk_total_b * (1 - disk_used_p / 100))

    payload = {
        "device_id": pc["id"],
        "hostname": pc["name"],
        "platform": pc["platform"],
        "ip_address": pc["ip"],
        "cpu_percent": cpu,
        "memory": {
            "used_percent": ram_used_p,
            "total_bytes": ram_total_b,
            "used_bytes": ram_used_b
        },
        "disk": {
            "used_percent": disk_used_p,
            "total_bytes": disk_total_b,
            "free_bytes": disk_free_b
        },
        "uptime_seconds": random.randint(3600, 180000)
    }

    req = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-LabPulse-Key", API_KEY)

    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def main():
    print("==================================================")
    print("  LabPulse UZ — Sinf Kompyuterlari Simulyatori")
    print(f"  Server: {SERVER_URL}")
    print(f"  Kompaniya Kaliti: {API_KEY}")
    print(f"  Kuzatilayotgan kompyuterlar soni: {len(COMPUTERS)} ta")
    print("==================================================")
    print("Simulyatsiya boshlandi (To'xtatish uchun: Ctrl + C)...\n")

    while True:
        statuses = []
        for pc in COMPUTERS:
            ok = send_simulated_heartbeat(pc)
            statuses.append(f"{pc['id']}: {'OK' if ok else 'FAIL'}")
        
        sys.stdout.write(f"\r[{time.strftime('%H:%M:%S')}] Signal yuborildi: " + " | ".join(statuses))
        sys.stdout.flush()
        time.sleep(4)


if __name__ == "__main__":
    main()
