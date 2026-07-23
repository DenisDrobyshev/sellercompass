"""FastAPI entrypoint."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from core import __version__
from core.api.health import router as health_router
from core.api.stages import router as stages_router

_INDEX = Path(__file__).resolve().parent / "web" / "index.html"

app = FastAPI(title="SellerHelper", version=__version__)
app.include_router(health_router)
app.include_router(stages_router)


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    """Serve the single-page web UI."""
    return FileResponse(_INDEX)


@app.get("/meta")
def meta() -> dict:
    return {"name": "SellerHelper", "version": __version__, "docs": "/docs"}
