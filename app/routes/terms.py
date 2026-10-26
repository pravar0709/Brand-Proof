"""Terms CRUD routes – manager only for writes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Term
from app.schemas import TermCreate, TermUpdate, TermOut
from app.auth import require_role
from app.audit import write_audit

router = APIRouter(prefix="/api/terms", tags=["terms"])


@router.get("", response_model=List[TermOut])
def list_terms(db: Session = Depends(get_db)):
    return db.query(Term).order_by(Term.kind, Term.term).all()


@router.post("", response_model=TermOut)
def create_term(
    data: TermCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("manager")),
):
    term = Term(**data.model_dump())
    db.add(term)
    db.commit()
    db.refresh(term)
    write_audit(db, user["name"], "term_created", f"Term: {term.term}", term.kind)
    return term


@router.put("/{term_id}", response_model=TermOut)
def update_term(
    term_id: int,
    data: TermUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("manager")),
):
    term = db.query(Term).filter(Term.id == term_id).first()
    if not term:
        raise HTTPException(404, "Term not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(term, key, val)
    db.commit()
    db.refresh(term)
    write_audit(db, user["name"], "term_updated", f"Term: {term.term}", "")
    return term


@router.delete("/{term_id}")
def delete_term(
    term_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("manager")),
):
    term = db.query(Term).filter(Term.id == term_id).first()
    if not term:
        raise HTTPException(404, "Term not found")
    db.delete(term)
    db.commit()
    write_audit(db, user["name"], "term_deleted", f"Term #{term_id}", "")
    return {"ok": True}
