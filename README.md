# LabPulse UZ — Kompyuter Laboratoriyalari Monitoring va Diagnostika Paneli

**Versiya:** 1.0 (MVP)  
**Til:** O‘zbek tili (Lotin yozuvi)  
**Asosiy qiymat taklifi:** *“Kompyuteringizda nima muammo borligini tez ko‘ring, sababi va xavfsiz yechimini o‘zbek tilida tushuning.”*

---

## 1. Loyiha haqida
**LabPulse UZ** — kompyuter sinflari, o‘quv markazlari va kichik ofislarga kompyuterlar hamda tarmoq holatini tushunishga yordam beradigan professional monitoring va diagnostika platformasi. 

Dastur CPU, RAM, disk, operatsion tizim va tarmoq parametrlarini real vaqtda kuzatadi, qoidalarga asoslangan shaffof o‘zbekcha tashxis qo‘yadi, xavfsiz tavsiyalar beradi va rasmiy hisobotlarni JSON yoki chop etish formatida taqdim etadi.

### Netdata bilan munosabati
LabPulse UZ monitoring vositalarining (shu jumladan Netdata) umumiy vazifalaridan ilhomlangan holda, butunlay **mustaqil va original interfeys**, o‘zbekcha diagnostika qoidalari va soddalashtirilgan ish jarayoniga ega. Tizim metrikalari to‘g‘ridan-to‘g‘ri `psutil` orqali lokal kompyuterdan olinadi. Netdata ulanmagan bo‘lsa, ulanmagan deb ko‘rsatiladi.

---

## 2. Asosiy Imkoniyatlar (MVP v1.0)
1. **Umumiy ko‘rinish (Dashboard):**
   - Lokal kompyuterning haqiqiy ko‘rsatkichlari (CPU %, RAM %, Asosiy disk bo‘sh joyi, Tarmoq).
   - CPU va RAM o‘zgarishini ko‘rsatuvchi dinamik jonli grafik (HTML5 Canvas).
   - Tizim umumiy holati indikatori (Barqaror / Diqqat / Muhim).
   - Avtomatik sozlanadigan yangilanish oralig‘i (3s, 5s, 10s, 30s).
2. **Kompyuterlar ro‘yxati (`/devices`):**
   - Mahalliy kompyuter haqiqiy ma’lumotlar bilan ko‘rsatiladi.
   - O‘quv sinfidagi boshqa kompyuterlar namunasi aniq `Demo ma'lumot` belgisi bilan ajratilgan (hech qachon soxta ulanish yasalmaydi).
3. **Diagnostika (`/diagnostics`):**
   - CPU, RAM, Disk, DNS yechimi va Ping ulanish testi.
   - Har bir topilma uchun: *nima aniqlandi*, *bu nimani anglatadi* va *xavfsiz keyingi qadam*.
   - Xato yoki ulanish yo‘qligi yashirilmaydi, ochiq va xolis xabar beriladi.
4. **Ogohlantirishlar (`/alerts`):**
   - Muhim, Diqqat va Ma’lumot darajalaridagi hodisalar jurnali.
   - Takrorlanuvchi shovqinni oldini oluvchi Cooldown / Debounce mexanizmi.
   - Alertlarni “ko‘rib chiqildi” (acknowledge) deb belgilash.
   - Masofaviy qurilma 35 soniya telemetriya yubormasa offline ogohlantirishi, qayta ulanganda tiklanish hodisasi SQLite’da saqlanadi.
5. **Hisobotlar (`/reports`):**
   - Bir tugma orqali to‘liq tizim holati hisobotini shakllantirish.
   - JSON formatida yuklab olish.
   - Chop etish yoki PDF sifatida saqlash uchun qulay toza ko‘rinish (`/reports/{id}/view`).
6. **Sozlamalar (`/settings`):**
   - Dark va Light temalar (tanlov brauzerda eslab qolinadi).
   - Yangilanish tezligi va diagnostika manzilini o‘zgartirish.
   - Threshold (ogohlantirish chegaralari) parametrlarini sozlash.

---

## 3. Texnik Stek
- **Backend:** Python 3.11+, FastAPI, Uvicorn
- **Frontend:** Jinja2 shablonlari, Vanilla JavaScript (hech qanday og‘ir build pipeline talab etilmaydi), Zamonaviy responsive CSS (Dark/Light design tokens)
- **Telemetriya:** `psutil` (haqiqiy tizim parametrlari)
- **Tarmoq diagnostikasi:** Python `socket`, xavfsiz `subprocess` (shell=False)
- **Testlash:** `pytest`, `pytest-asyncio`, FastAPI `TestClient`

---

## 4. O‘rnatish va Ishga tushirish

### Windows uchun tezkor ishga tushirish (Tavsiya etiladi):
Loyiha papkasidagi `start_windows.bat` faylini ikki marta bosing. Ushbu skript:
1. Python mavjudligini tekshiradi;
2. `venv` virtual muhitini yaratadi;
3. Kerakli kutubxonalarni o‘rnatadi;
4. Serverni `http://127.0.0.1:8000` manzilida ishga tushiradi.

### Qo‘lda ishga tushirish (Terminal orqali):
```powershell
# 1. Virtual muhit yaratish va faollashtirish
python -m venv venv
.\venv\Scripts\activate

# 2. Kutubxonalarni o'rnatish
pip install -r requirements.txt

# 3. Serverni ishga tushirish
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Brauzerda oching: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 5. Loyiha Tuzilmasi
```text
LabPulse UZ/
├── app/
│   ├── config.py                 # Markaziy konfiguratsiya va chegaralar
│   ├── main.py                   # FastAPI asosiy ilovasi
│   ├── routers/
│   │   ├── api.py                # REST API endpointlari (/api/metrics, /api/health va h.k.)
│   │   └── pages.py              # Jinja2 sahifalar routeri
│   ├── services/
│   │   ├── system_metrics.py     # psutil lokal telemetriyasi
│   │   ├── network_diagnostics.py# DNS va Ping tekshiruvlari
│   │   ├── diagnostic_rules.py   # O'zbekcha tashxis va tavsiya qoidalari
│   │   ├── alerts.py             # Ogohlantirishlar va cooldown
│   │   └── reports.py            # JSON hisobotlar generatori
│   ├── static/
│   │   ├── assets/logo.svg       # Original SVG logo (impuls/orbit)
│   │   ├── css/app.css           # To'liq dizayn tizimi (Dark/Light)
│   │   └── js/
│   │       ├── app.js            # Tema va umumiy yordamchilar
│   │       ├── dashboard.js      # Jonli telemetriya va grafik
│   │       └── diagnostics.js    # Interaktiv diagnostika logikasi
│   └── templates/
│       ├── base.html             # Asosiy shablon (Sidebar, Header)
│       ├── dashboard.html        # Bosh sahifa
│       ├── devices.html          # Kompyuterlar ro'yxati
│       ├── diagnostics.html      # Diagnostika sahifasi
│       ├── alerts.html           # Ogohlantirishlar
│       ├── reports.html          # Hisobotlar ro'yxati
│       ├── report_view.html      # Chop etish uchun sahifa
│       └── settings.html         # Sozlamalar sahifasi
├── tests/
│   ├── test_metrics.py           # psutil telemetriya testlari
│   ├── test_diagnostics.py       # Qoidalar va manzil validatsiyasi
│   ├── test_api.py               # API va sahifalar integratsion testlari
│   └── test_alerts_settings.py   # Ogohlantirishlar oqimi testlari
├── requirements.txt              # Python bog'liqliklari
├── start_windows.bat             # Windows uchun bir tugmali start skripti
├── .env.example                  # Namuna muhit o'zgaruvchilari
├── .gitignore                    # Git istisnolari
└── README.md                     # Hujjat (ushbu fayl)
```

---

## 6. Testlarni Ishga tushirish
Barcha testlarni tekshirish uchun:
```powershell
python -m pytest -v
```

---

## 7. Xavfsizlik va Shaffoflik Chegaralari
- Standart server faqat lokal `127.0.0.1` manziliga ulanadi (tashqi tarmoqqa ochiq emas).
- Diagnostika so‘rovlarida manzil qat’iy tekshiriladi (Command Injection xavfi yo‘q, `shell=False`).
- Hech qanday shaxsiy fayllar o‘chirilmaydi yoki Windows tizim fayllari ruxsatsiz o‘zgartirilmaydi.
- Tashqi serverlarga yashirin telemetriya yuborilmaydi.
- Demo qurilmalar doimo ochiqchasiga `Demo ma'lumot` deb tamg‘alanadi.
