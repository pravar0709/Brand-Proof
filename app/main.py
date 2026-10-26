"""BrandProof – Brand governance web app. Main FastAPI application."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.db import create_tables, seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables, seed data."""
    create_tables()
    seed_database()
    yield


app = FastAPI(
    title="BrandProof",
    description="Brand-governance review tool – Cite or Abstain",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Health check ──────────────────────────────────────────────────────
@app.get("/healthz")
def healthz():
    return {"status": "ok"}


# ── Static files (SPA) ───────────────────────────────────────────────
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def serve_spa():
    return FileResponse(os.path.join(static_dir, "index.html"))
