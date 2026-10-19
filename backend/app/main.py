from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app import models  # noqa: F401  регистрирует таблицы в metadata
from app.ai import router as ai_router
from app.auth import router as auth_router
from app.database import Base, engine
from app.presets import router as presets_router
from app.songs import router as songs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="AI Song Builder", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(presets_router)
app.include_router(songs_router)
app.include_router(ai_router)


@app.get("/health")
def health():
    return {"status": "ok"}
