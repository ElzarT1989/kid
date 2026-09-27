from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.admin import router as admin_router
from app.api.player import router as player_router
from app.config import settings
from app.database import init_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    yield


app = FastAPI(title="KidsEdu AI", lifespan=lifespan)

# Детский плеер (PWA) обращается к backend с другого origin (Vite dev server
# в разработке, отдельный домен/порт в проде) — CORS открыт полностью, так
# как API не содержит аутентификации и не рассчитан на публичный доступ
# (устройство работает в изолированной локальной сети/kiosk-режиме).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)
app.include_router(player_router)

Path(settings.video_storage_path).mkdir(parents=True, exist_ok=True)
Path(settings.tts_cache_path).mkdir(parents=True, exist_ok=True)
app.mount("/media/videos", StaticFiles(directory=settings.video_storage_path), name="videos")
app.mount("/media/tts", StaticFiles(directory=settings.tts_cache_path), name="tts")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
