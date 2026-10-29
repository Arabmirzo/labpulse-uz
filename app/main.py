"""
LabPulse UZ — Asosiy FastAPI Ilovasi.
"""
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers.api import router as api_router
from app.routers.pages import router as pages_router
from app.services.system_metrics import collect_metrics

# Yo'llar qat'iy ravishda ushbu fayl manziliga nisbatan aniqlanadi
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Server ishga tushganda dastlabki psutil o'lchovini olish
    try:
        collect_metrics()
    except Exception as exc:
        print(f"[LabPulse UZ] Dastlabki telemetriya yuklanmadi: {exc}")
    yield


app = FastAPI(
    title="LabPulse UZ",
    description="Kompyuter sinflari va kichik ofislar uchun o'zbekcha monitoring va diagnostika paneli.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan
)

# Statik fayllarni ulash (/static/...)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Routerlarni ro'yxatdan o'tkazish
app.include_router(pages_router)
app.include_router(api_router)
