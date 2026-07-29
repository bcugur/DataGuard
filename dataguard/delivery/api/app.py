"""FastAPI application factory.

Creates and configures the DataGuard web application.
Serves the static dashboard and mounts the API router.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from dataguard import __version__
from dataguard.delivery.api.routes.preview import router as preview_router
from dataguard.delivery.api.routes.validate import router as validate_router
from dataguard.shared.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

_STATIC_DIR = Path(__file__).parent / "static"

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="DataGuard",
    description="Data Quality Platform — Web Dashboard",
    version=__version__,
    docs_url="/api/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes ─────────────────────────────────────────────────────────────
app.include_router(validate_router)
app.include_router(preview_router)

# ── Static files ───────────────────────────────────────────────────────────
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    """Serve the main dashboard HTML."""
    return FileResponse(str(_STATIC_DIR / "index.html"))


@app.get("/api/health", tags=["system"])
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": __version__}
