"""BrandProof – Brand governance web app. Main FastAPI application."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db import create_tables, seed_database, get_db
from app.models import User
from app.auth import create_token, get_current_user
from app.audit import write_audit
from app.schemas import DemoLoginRequest, TokenResponse, UserOut

# Import routers
from app.routes.guidelines import router as guidelines_router
from app.routes.ledger import router as ledger_router
from app.routes.terms import router as terms_router
from app.routes.review import router as review_router
from app.routes.workflow import router as workflow_router
from app.routes.disclosure import router as disclosure_router


import asyncio
import httpx as _httpx
import logging

_logger = logging.getLogger(__name__)

# Self-ping interval (seconds) – keeps Render free-tier awake
_SELF_PING_INTERVAL = 13 * 60  # 13 minutes


async def _self_ping():
    """Background task: ping own /healthz every 13 min to prevent Render cold starts."""
    # Only run on Render (RENDER env var is auto-set by Render)
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "")
    if not render_url:
        _logger.info("Not on Render — self-ping disabled")
        return

    healthz_url = f"{render_url}/healthz"
    _logger.info(f"Self-ping enabled → {healthz_url} every {_SELF_PING_INTERVAL}s")

    while True:
        await asyncio.sleep(_SELF_PING_INTERVAL)
        try:
            async with _httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(healthz_url)
                _logger.debug(f"Self-ping: {resp.status_code}")
        except Exception as e:
            _logger.warning(f"Self-ping failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables, seed data, start keep-alive ping."""
    create_tables()
    seed_database()
    # Launch self-ping background task
    ping_task = asyncio.create_task(_self_ping())
    yield
    ping_task.cancel()



app = FastAPI(
    title="BrandProof",
    description="Brand-governance review tool – Cite or Abstain",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health check ──────────────────────────────────────────────────────
@app.get("/healthz")
def healthz():
    return {"status": "ok"}


# ── Demo auth ─────────────────────────────────────────────────────────
DEMO_USERS = {
    "creator": {"user_id": 1, "name": "Asha", "role": "creator"},
    "manager": {"user_id": 2, "name": "Meera", "role": "manager"},
    "reviewer": {"user_id": 3, "name": "Rohan", "role": "reviewer"},
}


@app.post("/api/auth/demo")
def demo_login(data: DemoLoginRequest, db: Session = Depends(get_db)):
    user_info = DEMO_USERS.get(data.role)
    if not user_info:
        from fastapi import HTTPException
        raise HTTPException(400, f"Invalid role: {data.role}")

    token = create_token(user_info["user_id"], user_info["role"], user_info["name"])
    write_audit(db, user_info["name"], "login", f"User #{user_info['user_id']}", f"Role: {data.role}")

    return {
        "token": token,
        "user": user_info,
    }


@app.get("/api/me")
def get_me(user: dict = Depends(get_current_user)):
    return user


# ── Register routers ─────────────────────────────────────────────────
app.include_router(guidelines_router)
app.include_router(ledger_router)
app.include_router(terms_router)
app.include_router(review_router)
app.include_router(workflow_router)
app.include_router(disclosure_router)


# ── Static files (SPA) ───────────────────────────────────────────────
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def serve_spa():
    return FileResponse(os.path.join(static_dir, "index.html"))
