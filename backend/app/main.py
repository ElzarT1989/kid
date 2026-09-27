from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.admin import router as admin_router
from app.api.player import router as player_router
from app.database import init_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    yield


app = FastAPI(title="KidsEdu AI", lifespan=lifespan)

app.include_router(admin_router)
app.include_router(player_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
