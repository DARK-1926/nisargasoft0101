from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from backend.app.config import settings
from backend.app.db import close_db, init_db
from backend.app.logging import configure_logging
from backend.app.metrics import MetricsMiddleware
from backend.app.mongo import mongo_archive
from backend.app.notifications import notifier
from backend.app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_json)
    await init_db()
    await mongo_archive.connect()
    app.state.mongo_archive = mongo_archive
    app.state.notifier = notifier
    yield
    await mongo_archive.close()
    await close_db()


app = FastAPI(
    title="Amazon India Bearing Price Monitor",
    version="0.1.0",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

allowed_origins = {
    settings.frontend_origin,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MetricsMiddleware)
app.include_router(router)
