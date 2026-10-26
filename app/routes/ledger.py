"""Claim Ledger CRUD routes – manager only for writes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import LedgerEntry
from app.schemas import LedgerCreate, LedgerUpdate, LedgerOut
from app.auth import get_current_user, require_role
from app.audit import write_audit

router = APIRouter(prefix="/api/ledger", tags=["ledger"])


@router.get("", response_model=List[LedgerOut])
def list_ledger(db: Session = Depends(get_db)):
    return db.query(LedgerEntry).order_by(LedgerEntry.id).all()


@router.get("/{entry_id}", response_model=LedgerOut)
def get_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(LedgerEntry).filter(LedgerEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(404, "Ledger entry not found")
    return entry


@router.post("", response_model=LedgerOut)
def create_entry(
    data: LedgerCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("manager")),
):
    entry = LedgerEntry(**data.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    write_audit(db, user["name"], "ledger_created", f"Ledger #{entry.id}", entry.claim[:100])
    return entry


@router.put("/{entry_id}", response_model=LedgerOut)
def update_entry(
    entry_id: int,
    data: LedgerUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("manager")),
):
    entry = db.query(LedgerEntry).filter(LedgerEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(404, "Ledger entry not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(entry, key, val)
    db.commit()
    db.refresh(entry)
    write_audit(db, user["name"], "ledger_updated", f"Ledger #{entry.id}", "")
    return entry


@router.delete("/{entry_id}")
def delete_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("manager")),
):
    entry = db.query(LedgerEntry).filter(LedgerEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(404, "Ledger entry not found")
    db.delete(entry)
    db.commit()
    write_audit(db, user["name"], "ledger_deleted", f"Ledger #{entry_id}", "")
    return {"ok": True}
