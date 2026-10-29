@echo off
chcp 65001 > nul
title LabPulse UZ — Ishga tushirish paneli
echo ============================================================
echo           LabPulse UZ — Monitoring va Diagnostika
echo ============================================================
echo.

:: 1. Python mavjudligini tekshirish
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [XATOLIK] Python kompyuteringizda topilmadi!
    echo Iltimos, Python 3.11 yoki undan yuqori versiyasini o'rnating:
    echo https://www.python.org/downloads/
    echo O'rnatishda "Add python.exe to PATH" katakchasini belgilashni unutmang.
    echo.
    pause
    exit /b 1
)

:: 2. Virtual environment (venv) tekshirish va yaratish
if not exist "venv" (
    echo [1/3] Virtual muhit (venv) yaratilmoqda...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [XATOLIK] Virtual muhitni yaratishda xatolik yuz berdi!
        pause
        exit /b 1
    )
)

:: 3. Venv'ni faollashtirish va kutubxonalarni tekshirish
echo [2/3] Kerakli kutubxonalar tekshirilmoqda...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul 2>nul
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [XATOLIK] Kutubxonalarni o'rnatishda xatolik yuz berdi!
    pause
    exit /b 1
)

:: 4. Serverni ishga tushirish
echo [3/3] LabPulse UZ serveri ishga tushirilmoqda...
echo.
echo ============================================================
echo   Dastur muvaffaqiyatli ishga tushdi!
echo   Brauzeringizda quyidagi manzilni oching:
echo   --> http://127.0.0.1:8000
echo ============================================================
echo   Serverni to'xtatish uchun: Ctrl + C
echo.

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

if %errorlevel% neq 0 (
    echo.
    echo [XATOLIK] Server kutilmaganda to'xtadi!
    pause
)
