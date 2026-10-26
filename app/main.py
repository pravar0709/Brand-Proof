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
