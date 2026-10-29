@echo off
chcp 65001 > nul
title LabPulse UZ — Agentni O'rnatish
echo ============================================================
echo        LabPulse UZ — Kompyuterga Agentni O'rnatish
echo ============================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [XATOLIK] Python topilmadi! Iltimos, Python 3.10+ o'rnating.
    pause
    exit /b 1
)

python -m pip install psutil >nul 2>nul

echo.
python "%~dp0labpulse_agent.py"
pause
