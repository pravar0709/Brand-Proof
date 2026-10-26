"""Audit logging – writes structured entries to audit_log table."""

from datetime import datetime
from app.models import AuditLog


def write_audit(db, actor: str, action: str, entity: str = "", detail: str = ""):
    """Write an audit log entry."""
    entry = AuditLog(
        actor=actor,
        action=action,
        entity=entity,
        detail=detail,
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
