"""
O'zbekcha qoidalarga asoslangan diagnostika va tahlil moduli.
Barcha xulosalar, sabablar va xavfsiz tavsiyalar o'zbek tilida (lotin yozuvida).
Hech qanday generativ AI ishlatilmaydi — qoidalar shaffof va qat'iy sinovdan o'tgan.
"""
from typing import Any, Dict, List
from app.config import get_settings


def analyze_metrics(metrics: Dict[str, Any], network_results: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Tizim metrikalari va tarmoq holatini qoidalar asosida tekshirib,
    topilmalar ro'yxatini shakllantiradi.
    
    Darajalar:
    - "Ma'lumot" (Info)
    - "Diqqat" (Warning)
    - "Muhim" (Critical)
    """
    settings = get_settings()
    th = settings.get("thresholds", {})
    cpu_crit = th.get("cpu_critical", 90)
    ram_crit = th.get("ram_critical", 90)
    ram_warn = th.get("ram_warning", 80)
    disk_crit = th.get("disk_critical", 10)  # bo'sh joy foizi
    disk_warn = th.get("disk_warning", 20)  # bo'sh joy foizi

    findings: List[Dict[str, Any]] = []

    # 1. CPU Tahlili
    cpu_val = metrics.get("cpu_percent")
    if cpu_val is None:
        findings.append({
            "category": "CPU",
            "level": "Diqqat",
            "title": "CPU ko'rsatkichi aniqlanmadi",
            "detail": "Protsessor yuklanishini hisoblashda ma'lumot olinmadi.",
            "recommendation": "Tizim ruxsatlari yoki monitoring xizmatini tekshiring."
        })
    elif cpu_val >= cpu_crit:
        findings.append({
            "category": "CPU",
            "level": "Muhim",
            "title": f"CPU yuklanishi o'ta yuqori ({cpu_val}%)",
            "detail": f"Protsessor quvvati {cpu_crit}% dan oshib ketgan. Bu tizim qotishiga yoki dasturlar sekinlashishiga olib kelishi mumkin.",
            "recommendation": "Vazifalar boshqaruvchisi (Task Manager) orqali eng ko'p CPU sarflayotgan jarayonlarni aniqlang va keraksiz og'ir dasturlarni yoping."
        })
    elif cpu_val >= 70:
        findings.append({
            "category": "CPU",
            "level": "Diqqat",
            "title": f"CPU sezilarli darajada yuklangan ({cpu_val}%)",
            "detail": "Protsessor o'rtacha darajadan ko'proq ishlamoqda.",
            "recommendation": "Fon rejimida ishlayotgan yangilanishlar yoki ilovalarni kuzating."
        })
    else:
        findings.append({
            "category": "CPU",
            "level": "Ma'lumot",
            "title": f"CPU holati me'yorda ({cpu_val}%)",
            "detail": "Protsessor yuklanishi xavfsiz chegarada ishlamoqda.",
            "recommendation": "Hech qanday qo'shimcha chora talab etilmaydi."
        })

    # 2. RAM Tahlili
    mem = metrics.get("memory", {})
    ram_val = mem.get("used_percent")
    if ram_val is None:
        findings.append({
            "category": "RAM",
            "level": "Diqqat",
            "title": "RAM ko'rsatkichi aniqlanmadi",
            "detail": "Operativ xotira ma'lumotlarini o'qib bo'lmadi.",
            "recommendation": "Tizim drayveri yoki ruxsatlarini ko'rib chiqing."
        })
    elif ram_val >= ram_crit:
        findings.append({
            "category": "RAM",
            "level": "Muhim",
            "title": f"Operativ xotira deyarli to'lgan ({ram_val}%)",
            "detail": f"RAM ishlatilishi {ram_crit}% dan oshgan. Kompyuter sekinlashishi va yangi oynalar ochilmasligi mumkin.",
            "recommendation": "Brauzerdagi ortiqcha varaqlarni yoki ko'p xotira yeyotgan dasturlarni yopish tavsiya etiladi."
        })
    elif ram_val >= ram_warn:
        findings.append({
            "category": "RAM",
            "level": "Diqqat",
            "title": f"Operativ xotira to'lib bormoqda ({ram_val}%)",
            "detail": f"Xotira ishlatilishi {ram_warn}% dan yuqori.",
            "recommendation": "Yaqin orada xotira yetishmovchiligi yuzaga kelmasligi uchun keraksiz ilovalarni yakunlang."
        })
    else:
        findings.append({
            "category": "RAM",
            "level": "Ma'lumot",
            "title": f"RAM holati barqaror ({ram_val}%)",
            "detail": "Operativ xotira yetarli miqdorda bo'sh.",
            "recommendation": "Tizim xotirasi me'yoriy rejimda ishlayapti."
        })

    # 3. Disk Tahlili
    disk = metrics.get("disk", {})
    disk_used = disk.get("used_percent")
    total_b = disk.get("total_bytes", 0)
    free_b = disk.get("free_bytes", 0)
    free_percent = round((free_b / total_b * 100), 1) if total_b > 0 else None

    if disk_used is None or free_percent is None:
        findings.append({
            "category": "Disk",
            "level": "Diqqat",
            "title": "Disk holatini aniqlab bo'lmadi",
            "detail": "Asosiy disk hajmini tekshirishda xatolik yuz berdi.",
            "recommendation": "Disk drayverlari va fayl tizimi holatini ko'zdan kechiring."
        })
    elif free_percent <= disk_crit:
        free_gb = round(free_b / (1024**3), 1)
        findings.append({
            "category": "Disk",
            "level": "Muhim",
            "title": f"Diskda bo'sh joy keskin kam ({free_percent}%, {free_gb} GB qolgan)",
            "detail": f"Tizim diski xavfli darajada to'lib qolgan (erkin joy {disk_crit}% dan past). Bu operatsion tizim faoliyatini to'xtatishi mumkin.",
            "recommendation": "Windows 'Disk tozalash' (Disk Cleanup) vositasini ishga tushiring, vaqtinchalik (Temp) va yuklab olingan fayllarni ko'zdan kechiring."
        })
    elif free_percent <= disk_warn:
        free_gb = round(free_b / (1024**3), 1)
        findings.append({
            "category": "Disk",
            "level": "Diqqat",
            "title": f"Disk bo'sh joyi kamaymoqda ({free_percent}%, {free_gb} GB qolgan)",
            "detail": f"Erkin joy {disk_warn}% dan kam.",
            "recommendation": "Keraksiz katta hajmli fayllarni boshqa diskka yoki bulutga ko'chiring."
        })
    else:
        findings.append({
            "category": "Disk",
            "level": "Ma'lumot",
            "title": f"Diskda yetarli bo'sh joy mavjud ({free_percent}% erkin)",
            "detail": f"Asosiy disk holati barqaror ({disk_used}% band).",
            "recommendation": "Fayl tizimi me'yorda ishlayapti."
        })

    # 4. Tarmoq Tahlili (agar mavjud bo'lsa)
    if network_results:
        dns_res = network_results.get("dns", {})
        ping_res = network_results.get("ping", {})

        if dns_res.get("status") != "success":
            findings.append({
                "category": "Tarmoq (DNS)",
                "level": "Diqqat",
                "title": "DNS server javob bermadi",
                "detail": f"DNS so'rovi muvaffaqiyatsiz bo'ldi: {dns_res.get('message', 'Noma\'lum xatolik')}",
                "recommendation": "Tarmoq sozlamalarida DNS manzilini tekshiring (masalan, 8.8.8.8 yoki 1.1.1.1) yoki routerni qayta ishga tushiring."
            })
        else:
            findings.append({
                "category": "Tarmoq (DNS)",
                "level": "Ma'lumot",
                "title": f"DNS yechimi tezkor ({dns_res.get('latency_ms')} ms)",
                "detail": f"Domen muvaffaqiyatli aniqlandi: {dns_res.get('target')}",
                "recommendation": "DNS xizmati to'g'ri sozlangan."
            })

        if ping_res.get("status") != "success":
            findings.append({
                "category": "Tarmoq (Ping)",
                "level": "Diqqat",
                "title": f"Tarmoqqa ulanish yo'q yoki javob vaqti oshdi",
                "detail": f"'{ping_res.get('target')}' manziliga ping javob bermadi: {ping_res.get('message', 'Paketlar yo\'qoldi')}",
                "recommendation": "Tarmoq kabeli yoki Wi-Fi ulanishini tekshiring. Internet provayderi yoki router holatini ko'zdan kechiring."
            })
        else:
            findings.append({
                "category": "Tarmoq (Ping)",
                "level": "Ma'lumot",
                "title": f"Tarmoq ulanishi barqaror ({ping_res.get('latency_ms')} ms)",
                "detail": f"'{ping_res.get('target')}' manzilidan javob muvaffaqiyatli keldi.",
                "recommendation": "Kanal o'tkazuvchanligi va aloqa barqaror."
            })

    return findings


def get_system_summary_status(findings: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Topilmalar asosida umumiy tizim holati (yaxshi / diqqat / muhim).
    """
    levels = [f.get("level") for f in findings]
    if "Muhim" in levels:
        return {
            "status": "critical",
            "label": "Muhim e'tibor talab",
            "description": "Tizimda zudlik bilan bartaraf etilishi lozim bo'lgan jiddiy holat aniqlandi.",
            "color_class": "badge-critical"
        }
    elif "Diqqat" in levels:
        return {
            "status": "warning",
            "label": "Diqqat talab qilinadi",
            "description": "Ba'zi ko'rsatkichlar me'yordan chetlashgan, e'tibor qaratish tavsiya etiladi.",
            "color_class": "badge-warning"
        }
    else:
        return {
            "status": "good",
            "label": "Tizim barqaror",
            "description": "Barcha asosiy ko'rsatkichlar me'yorida ishlamoqda.",
            "color_class": "badge-success"
        }
