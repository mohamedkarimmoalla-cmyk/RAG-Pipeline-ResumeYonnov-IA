"""Application entrypoint for the FastAPI backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.pipeline_runs import router as pipeline_runs_router
from app.api.routes.summarize import router as summarize_router
from app.api.routes.summary import router as summary_router
from app.api.routes.upload import router as upload_router
from app.core.config import APP_NAME, APP_VERSION, CORS_ORIGINS
from app.api.routes.documents import router as documents_router
app = FastAPI(title=APP_NAME, version=APP_VERSION)

if CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS","DELETE"],
        allow_headers=["*"],
    )
app.include_router(documents_router)
app.include_router(health_router)
app.include_router(pipeline_runs_router)
app.include_router(upload_router)
app.include_router(summarize_router)
app.include_router(summary_router)
