"""Disclosure and Insights routes."""

import os
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import get_db
from app.models import Finding, LedgerEntry, Submission
from app.auth import get_current_user

router = APIRouter(prefix="/api", tags=["disclosure"])


@router.get("/insights")
def get_insights(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Basic analytics: top flagged rules, dispute counts, expiring ledger entries."""

    # Top flagged rules (by source_quote containing rule codes)
    top_rules = (
        db.query(
            Finding.source_type,
            Finding.source_id,
            func.count(Finding.id).label("count"),
        )
        .filter(Finding.source_type == "rule")
        .group_by(Finding.source_type, Finding.source_id)
        .order_by(func.count(Finding.id).desc())
        .limit(10)
        .all()
    )

    # Dispute counts
    disputes = (
        db.query(
            Finding.source_id,
            func.count(Finding.id).label("count"),
        )
        .filter(Finding.decision == "disputed")
        .group_by(Finding.source_id)
        .all()
    )

    # Ledger entries expiring in 30 days
    today = date.today()
    thirty_days = (today + timedelta(days=30)).isoformat()
    today_str = today.isoformat()
    expiring = (
        db.query(LedgerEntry)
        .filter(
            LedgerEntry.expires_on.isnot(None),
            LedgerEntry.expires_on <= thirty_days,
            LedgerEntry.expires_on >= today_str,
        )
        .all()
    )

    total_subs = db.query(Submission).count()
    total_findings = db.query(Finding).count()

    return {
        "top_flagged_rules": [
            {"source_id": r[1], "count": r[2]} for r in top_rules
        ],
        "dispute_counts": [
            {"source_id": d[0], "count": d[1]} for d in disputes
        ],
        "expiring_ledger": [
            {"id": e.id, "claim": e.claim, "expires_on": e.expires_on}
            for e in expiring
        ],
        "total_submissions": total_subs,
        "total_findings": total_findings,
    }


@router.get("/disclosure")
def get_disclosure():
    """AI and service disclosure information."""
    provider = os.environ.get("LLM_PROVIDER", "none")
    model = os.environ.get("LLM_MODEL", "not configured")

    return {
        "services": [
            {
                "name": "LLM Provider",
                "provider": provider if provider != "none" else "Not configured",
                "model": model if provider != "none" else "N/A",
                "purpose": "Supplementary claim verification for tone and context that rule-based checks cannot determine",
                "data_sent": "Only redacted text (emails, phone numbers, and confidential terms are masked before sending)",
            },
            {
                "name": "scikit-learn TF-IDF",
                "provider": "Local (no external calls)",
                "model": "TfidfVectorizer",
                "purpose": "Retrieval of relevant rules and ledger entries for context",
                "data_sent": "None (runs locally)",
            },
        ],
        "checks_by_code": [
            "Banned/preferred term detection",
            "Superlative, guarantee, and medical claim detection",
            "Number extraction and Ledger comparison",
            "Expired Ledger entry detection",
            "Tone analysis (exclamation marks, ALL CAPS, fear language)",
            "Emoji count and hashtag CamelCase accessibility check",
            "Readability (sentence length)",
            "Sunscreen reapply rule (R5)",
        ],
        "checks_by_ai": [
            "Contextual claim verification (only when code-based checks are inconclusive)",
            "Suggested rewrites (marked with AI badge)",
        ],
        "ai_usage": (
            "AI (LLM) is used only for supplementary verification of claims that cannot be "
            "fully resolved by deterministic rule-based checks. All AI-generated findings are "
            "clearly marked with an 'AI' badge. The AI's quoted evidence is independently verified "
            "against source text (quote check). If verification fails, the finding is downgraded "
            "to 'Unverified'."
        ),
        "data_handling": (
            "Only redacted text is sent to the LLM. Emails, phone numbers, and configurable "
            "confidential terms are masked before transmission. No data is stored by the LLM provider."
        ),
        "human_in_loop": (
            "BrandProof is a review aid, not an automated enforcer. No changes are auto-applied. "
            "Every finding requires a human decision: Accept, Edit, or Dispute. A reviewer must "
            "explicitly approve submissions. Creators can dispute any finding with a reason."
        ),
        "limitations": (
            "BrandProof is a review aid, not legal advice. It cannot guarantee regulatory compliance. "
            "AI-based findings may be incorrect and are always subject to human review. The system "
            "cannot process images, videos, or PDF files. Brand guidelines must be manually maintained."
        ),
        "development": (
            "This application was developed with AI coding assistance (Antigravity/Gemini and Claude) "
            "for planning and code generation. The seed brand (GlowLeaf) and all data are fictional/synthetic. "
            "No real confidential data is used."
        ),
    }
