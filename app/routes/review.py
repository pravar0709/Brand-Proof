"""Review routes: submission CRUD, review pipeline, findings decisions."""

import os
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from datetime import datetime

from app.db import get_db
from app.models import Submission, Version, Finding, Rule, LedgerEntry, Term
from app.schemas import (
    SubmissionCreate, SubmissionOut, FindingOut, FindingDecision,
    ReviewResult, ResubmitRequest, VersionOut,
)
from app.auth import get_current_user, require_role
from app.audit import write_audit
from app.ratelimit import review_limiter
from app.pipeline.orchestrate import review as run_review

router = APIRouter(prefix="/api", tags=["review"])


# ── Sample drafts ─────────────────────────────────────────────────────
@router.get("/samples")
def get_samples():
    seed_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "seed", "sample_drafts.json"
    )
    try:
        with open(seed_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"drafts": []}


# ── Submissions ───────────────────────────────────────────────────────
@router.get("/submissions", response_model=List[SubmissionOut])
def list_submissions(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if user["role"] == "creator":
        return db.query(Submission).filter(Submission.creator_id == user["user_id"]).order_by(Submission.id.desc()).all()
    return db.query(Submission).order_by(Submission.id.desc()).all()


@router.post("/submissions", response_model=SubmissionOut)
def create_submission(
    data: SubmissionCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("creator")),
):
    sub = Submission(
        title=data.title,
        creator_id=user["user_id"],
        status="draft",
        current_version=1,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    version = Version(
        submission_id=sub.id,
        version_no=1,
        text=data.text,
        created_at=datetime.utcnow(),
    )
    db.add(version)
    db.commit()

    write_audit(db, user["name"], "submission_created", f"Submission #{sub.id}", sub.title)
    return sub


@router.post("/submissions/upload", response_model=SubmissionOut)
async def upload_submission(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("creator")),
):
    """Upload a DOCX or TXT file as a submission."""
    if file.content_type == "text/plain" or file.filename.endswith(".txt"):
        content = await file.read()
        text = content.decode("utf-8")
    elif file.filename.endswith(".docx"):
        import io
        from docx import Document
        content = await file.read()
        doc = Document(io.BytesIO(content))
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    else:
        raise HTTPException(400, "Only .txt and .docx files are supported")

    sub = Submission(
        title=title,
        creator_id=user["user_id"],
        status="draft",
        current_version=1,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    version = Version(
        submission_id=sub.id,
        version_no=1,
        text=text,
        created_at=datetime.utcnow(),
    )
    db.add(version)
    db.commit()

    write_audit(db, user["name"], "submission_uploaded", f"Submission #{sub.id}", title)
    return sub


@router.get("/submissions/{sub_id}")
def get_submission(
    sub_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    sub = db.query(Submission).filter(Submission.id == sub_id).first()
    if not sub:
        raise HTTPException(404, "Submission not found")

    versions = db.query(Version).filter(Version.submission_id == sub_id).order_by(Version.version_no).all()
    findings = db.query(Finding).filter(Finding.submission_id == sub_id).order_by(Finding.id).all()

    from app.models import Comment, User
    comments = (
        db.query(Comment, User.name)
        .join(User, Comment.author_id == User.id)
        .filter(Comment.submission_id == sub_id)
        .order_by(Comment.created_at)
        .all()
    )

    creator = db.query(User).filter(User.id == sub.creator_id).first()

    return {
        "id": sub.id,
        "title": sub.title,
        "creator_id": sub.creator_id,
        "creator_name": creator.name if creator else "Unknown",
        "status": sub.status,
        "current_version": sub.current_version,
        "versions": [
            {
                "id": v.id,
                "version_no": v.version_no,
                "text": v.text,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ],
        "findings": [
            {
                "id": f.id,
                "submission_id": f.submission_id,
                "version_id": f.version_id,
                "category": f.category,
                "severity": f.severity,
                "explanation": f.explanation,
                "source_type": f.source_type,
                "source_id": f.source_id,
                "source_quote": f.source_quote,
                "span_start": f.span_start,
                "span_end": f.span_end,
                "flagged_text": f.flagged_text,
                "verdict": f.verdict,
                "confidence_label": f.confidence_label,
                "confidence_score": f.confidence_score,
                "suggestion": f.suggestion,
                "ai_generated": f.ai_generated,
                "decision": f.decision,
                "edited_text": f.edited_text,
                "dispute_reason": f.dispute_reason,
            }
            for f in findings
        ],
        "comments": [
            {
                "id": c.id,
                "submission_id": c.submission_id,
                "author_id": c.author_id,
                "author_name": name,
                "body": c.body,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c, name in comments
        ],
    }


# ── Review pipeline ──────────────────────────────────────────────────
@router.post("/submissions/{sub_id}/review")
async def review_submission(
    sub_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    # Rate limit
    review_limiter.check(request)

    sub = db.query(Submission).filter(Submission.id == sub_id).first()
    if not sub:
        raise HTTPException(404, "Submission not found")

    # Get the current version text
    version = (
        db.query(Version)
        .filter(Version.submission_id == sub_id, Version.version_no == sub.current_version)
        .first()
    )
    if not version:
        raise HTTPException(404, "Version not found")

    # Load rules, ledger, terms from DB
    rules = [
        {"id": r.id, "code": r.code, "title": r.title, "text": r.text,
         "category": r.category, "severity": r.severity}
        for r in db.query(Rule).all()
    ]
    ledger = [
        {"id": le.id, "claim": le.claim, "evidence": le.evidence,
         "allowed_wording": le.allowed_wording, "owner": le.owner,
         "expires_on": le.expires_on, "status": le.status}
        for le in db.query(LedgerEntry).all()
    ]
    terms = [
        {"id": t.id, "term": t.term, "kind": t.kind,
         "replacement": t.replacement, "rule_code": t.rule_code}
        for t in db.query(Term).all()
    ]

    # Clear old findings for this version
    db.query(Finding).filter(Finding.version_id == version.id).delete()
    db.commit()

    # Run the pipeline
    findings_data, ai_status = await run_review(version.text, rules, ledger, terms)

    # Store findings in DB
    for f_data in findings_data:
        finding = Finding(
            submission_id=sub.id,
            version_id=version.id,
            category=f_data.get("category", "general"),
            severity=f_data.get("severity", "medium"),
            explanation=f_data.get("explanation", ""),
            source_type=f_data.get("source_type", "none"),
            source_id=f_data.get("source_id"),
            source_quote=f_data.get("source_quote", ""),
            span_start=f_data.get("span_start"),
            span_end=f_data.get("span_end"),
            flagged_text=f_data.get("flagged_text", ""),
            verdict=f_data.get("verdict", "unverified"),
            confidence_label=f_data.get("confidence_label", "Medium"),
            confidence_score=f_data.get("confidence_score", 0.5),
            suggestion=f_data.get("suggestion", ""),
            ai_generated=f_data.get("ai_generated", False),
            decision="pending",
        )
        db.add(finding)

    sub.status = "in_review"
    db.commit()

    write_audit(db, user["name"], "review_run", f"Submission #{sub.id}",
                f"{len(findings_data)} findings, AI: {ai_status}")

    # Re-fetch findings
    stored_findings = db.query(Finding).filter(Finding.version_id == version.id).all()

    return {
        "submission_id": sub.id,
        "version_id": version.id,
        "findings_count": len(stored_findings),
        "ai_status": ai_status,
        "findings": [
            {
                "id": f.id,
                "submission_id": f.submission_id,
                "version_id": f.version_id,
                "category": f.category,
                "severity": f.severity,
                "explanation": f.explanation,
                "source_type": f.source_type,
                "source_id": f.source_id,
                "source_quote": f.source_quote,
                "span_start": f.span_start,
                "span_end": f.span_end,
                "flagged_text": f.flagged_text,
                "verdict": f.verdict,
                "confidence_label": f.confidence_label,
                "confidence_score": f.confidence_score,
                "suggestion": f.suggestion,
                "ai_generated": f.ai_generated,
                "decision": f.decision,
                "edited_text": f.edited_text or "",
                "dispute_reason": f.dispute_reason or "",
            }
            for f in stored_findings
        ],
    }


# ── Finding decisions ────────────────────────────────────────────────
@router.post("/findings/{finding_id}/decision")
def decide_finding(
    finding_id: int,
    data: FindingDecision,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("creator")),
):
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(404, "Finding not found")

    if data.decision == "disputed" and not data.dispute_reason:
        raise HTTPException(400, "Dispute reason is required")

    if data.decision == "edited" and not data.edited_text:
        raise HTTPException(400, "Edited text is required")

    finding.decision = data.decision
    if data.edited_text:
        finding.edited_text = data.edited_text
    if data.dispute_reason:
        finding.dispute_reason = data.dispute_reason

    db.commit()
    write_audit(db, user["name"], "finding_decision", f"Finding #{finding_id}", data.decision)

    return {"ok": True, "decision": data.decision}


# ── Resubmit ─────────────────────────────────────────────────────────
@router.post("/submissions/{sub_id}/resubmit")
async def resubmit(
    sub_id: int,
    data: ResubmitRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("creator")),
):
    sub = db.query(Submission).filter(Submission.id == sub_id).first()
    if not sub:
        raise HTTPException(404, "Submission not found")

    # Create new version
    new_version_no = sub.current_version + 1
    version = Version(
        submission_id=sub.id,
        version_no=new_version_no,
        text=data.text,
        created_at=datetime.utcnow(),
    )
    db.add(version)
    sub.current_version = new_version_no
    sub.status = "draft"
    db.commit()
    db.refresh(version)

    write_audit(db, user["name"], "resubmitted", f"Submission #{sub.id}", f"Version {new_version_no}")

    # Auto-run review on the new version
    review_limiter.check(request)

    rules = [
        {"id": r.id, "code": r.code, "title": r.title, "text": r.text,
         "category": r.category, "severity": r.severity}
        for r in db.query(Rule).all()
    ]
    ledger = [
        {"id": le.id, "claim": le.claim, "evidence": le.evidence,
         "allowed_wording": le.allowed_wording, "owner": le.owner,
         "expires_on": le.expires_on, "status": le.status}
        for le in db.query(LedgerEntry).all()
    ]
    terms = [
        {"id": t.id, "term": t.term, "kind": t.kind,
         "replacement": t.replacement, "rule_code": t.rule_code}
        for t in db.query(Term).all()
    ]

    findings_data, ai_status = await run_review(version.text, rules, ledger, terms)

    for f_data in findings_data:
        finding = Finding(
            submission_id=sub.id,
            version_id=version.id,
            category=f_data.get("category", "general"),
            severity=f_data.get("severity", "medium"),
            explanation=f_data.get("explanation", ""),
            source_type=f_data.get("source_type", "none"),
            source_id=f_data.get("source_id"),
            source_quote=f_data.get("source_quote", ""),
            span_start=f_data.get("span_start"),
            span_end=f_data.get("span_end"),
            flagged_text=f_data.get("flagged_text", ""),
            verdict=f_data.get("verdict", "unverified"),
            confidence_label=f_data.get("confidence_label", "Medium"),
            confidence_score=f_data.get("confidence_score", 0.5),
            suggestion=f_data.get("suggestion", ""),
            ai_generated=f_data.get("ai_generated", False),
            decision="pending",
        )
        db.add(finding)

    sub.status = "in_review"
    db.commit()

    return {
        "submission_id": sub.id,
        "version_no": new_version_no,
        "findings_count": len(findings_data),
        "ai_status": ai_status,
    }
