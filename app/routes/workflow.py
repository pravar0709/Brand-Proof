"""Workflow routes: comments, approve, request changes."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Submission, Finding, Comment, User
from app.schemas import CommentCreate, ApproveRequest
from app.auth import get_current_user, require_role
from app.audit import write_audit

router = APIRouter(prefix="/api/submissions", tags=["workflow"])


@router.post("/{sub_id}/comments")
def add_comment(
    sub_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    sub = db.query(Submission).filter(Submission.id == sub_id).first()
    if not sub:
        raise HTTPException(404, "Submission not found")

    comment = Comment(
        submission_id=sub_id,
        author_id=user["user_id"],
        body=data.body,
        created_at=datetime.utcnow(),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    write_audit(db, user["name"], "comment_added", f"Submission #{sub_id}", data.body[:100])

    return {
        "id": comment.id,
        "submission_id": comment.submission_id,
        "author_id": comment.author_id,
        "author_name": user["name"],
        "body": comment.body,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


@router.post("/{sub_id}/approve")
def approve_submission(
    sub_id: int,
    data: ApproveRequest = None,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("reviewer", "manager")),
):
    sub = db.query(Submission).filter(Submission.id == sub_id).first()
    if not sub:
        raise HTTPException(404, "Submission not found")

    # Check for pending findings
    pending = (
        db.query(Finding)
        .filter(Finding.submission_id == sub_id, Finding.decision == "pending")
        .count()
    )

    if pending > 0:
        override_reason = data.override_reason if data else None
        if not override_reason:
            raise HTTPException(
                400,
                f"Cannot approve: {pending} finding(s) still pending. "
                f"Provide an override_reason to approve anyway."
            )
        # Log the override
        write_audit(
            db, user["name"], "approval_override",
            f"Submission #{sub_id}",
            f"Overriding {pending} pending findings. Reason: {override_reason}"
        )

    sub.status = "approved"
    db.commit()

    write_audit(db, user["name"], "submission_approved", f"Submission #{sub_id}", "")

    return {"ok": True, "status": "approved"}


@router.post("/{sub_id}/request-changes")
def request_changes(
    sub_id: int,
    data: CommentCreate = None,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("reviewer", "manager")),
):
    sub = db.query(Submission).filter(Submission.id == sub_id).first()
    if not sub:
        raise HTTPException(404, "Submission not found")

    sub.status = "changes_requested"

    # Optionally add a comment with the reason
    if data and data.body:
        comment = Comment(
            submission_id=sub_id,
            author_id=user["user_id"],
            body=data.body,
            created_at=datetime.utcnow(),
        )
        db.add(comment)

    db.commit()

    write_audit(db, user["name"], "changes_requested", f"Submission #{sub_id}",
                data.body[:100] if data and data.body else "")

    return {"ok": True, "status": "changes_requested"}
