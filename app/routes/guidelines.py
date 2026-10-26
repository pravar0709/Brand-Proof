"""Guidelines (rules) CRUD routes – manager only for writes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Rule
from app.schemas import RuleCreate, RuleUpdate, RuleOut
from app.auth import get_current_user, require_role
from app.audit import write_audit

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("", response_model=List[RuleOut])
def list_rules(db: Session = Depends(get_db)):
    return db.query(Rule).order_by(Rule.code).all()


@router.get("/{rule_id}", response_model=RuleOut)
def get_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Rule not found")
    return rule


@router.post("", response_model=RuleOut)
def create_rule(
    data: RuleCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("manager")),
):
    existing = db.query(Rule).filter(Rule.code == data.code).first()
    if existing:
        raise HTTPException(400, f"Rule {data.code} already exists")
    rule = Rule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    write_audit(db, user["name"], "rule_created", f"Rule {rule.code}", rule.title)
    return rule


@router.put("/{rule_id}", response_model=RuleOut)
def update_rule(
    rule_id: int,
    data: RuleUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("manager")),
):
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Rule not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(rule, key, val)
    db.commit()
    db.refresh(rule)
    write_audit(db, user["name"], "rule_updated", f"Rule {rule.code}", "")
    return rule


@router.delete("/{rule_id}")
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("manager")),
):
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Rule not found")
    code = rule.code
    db.delete(rule)
    db.commit()
    write_audit(db, user["name"], "rule_deleted", f"Rule {code}", "")
    return {"ok": True}


@router.post("/import")
def import_rules(
    body: dict,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("manager")),
):
    """Import rules from pasted text. Splits by numbered lines (R1, R2, etc.) or paragraphs."""
    import re
    text = body.get("text", "")
    if not text.strip():
        raise HTTPException(400, "No text provided")

    # Try splitting by numbered patterns like "R1:", "R2.", "1.", "1)"
    parts = re.split(r'\n(?=R?\d+[\.\:\)]\s)', text.strip())
    preview = []
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        # Try to extract code from the beginning
        m = re.match(r'(R?\d+)[\.\:\)]\s*(.*)', part, re.DOTALL)
        if m:
            code = m.group(1) if m.group(1).startswith("R") else f"R{m.group(1)}"
            rest = m.group(2).strip()
        else:
            code = f"R{i+1}"
            rest = part

        # Split title from body at first period or newline
        title_split = re.split(r'[\.\n]', rest, maxsplit=1)
        title = title_split[0].strip()[:200]
        body_text = title_split[1].strip() if len(title_split) > 1 else title

        preview.append({
            "code": code,
            "title": title,
            "text": body_text,
            "category": "general",
            "severity": "medium",
        })

    if body.get("save"):
        for item in preview:
            existing = db.query(Rule).filter(Rule.code == item["code"]).first()
            if not existing:
                db.add(Rule(**item))
        db.commit()
        write_audit(db, user["name"], "rules_imported", "", f"{len(preview)} rules")
        return {"saved": len(preview), "rules": preview}

    return {"preview": preview}
