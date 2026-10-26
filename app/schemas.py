"""Pydantic schemas for API request/response validation."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


# ── Auth ──────────────────────────────────────────────────────────────
class DemoLoginRequest(BaseModel):
    role: str = Field(..., pattern="^(creator|manager|reviewer)$")

class TokenResponse(BaseModel):
    token: str
    user: "UserOut"

class UserOut(BaseModel):
    id: int
    name: str
    role: str
    class Config:
        from_attributes = True


# ── Rules ─────────────────────────────────────────────────────────────
class RuleCreate(BaseModel):
    code: str
    title: str
    text: str
    category: str
    severity: str = "medium"

class RuleUpdate(BaseModel):
    title: Optional[str] = None
    text: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None

class RuleOut(BaseModel):
    id: int
    code: str
    title: str
    text: str
    category: str
    severity: str
    class Config:
        from_attributes = True


# ── Ledger ────────────────────────────────────────────────────────────
class LedgerCreate(BaseModel):
    claim: str
    evidence: str
    allowed_wording: str = ""
    owner: str = "GlowLeaf"
    expires_on: Optional[str] = None
    status: str = "active"

class LedgerUpdate(BaseModel):
    claim: Optional[str] = None
    evidence: Optional[str] = None
    allowed_wording: Optional[str] = None
    owner: Optional[str] = None
    expires_on: Optional[str] = None
    status: Optional[str] = None

class LedgerOut(BaseModel):
    id: int
    claim: str
    evidence: str
    allowed_wording: str
    owner: str
    expires_on: Optional[str]
    status: str
    class Config:
        from_attributes = True


# ── Terms ─────────────────────────────────────────────────────────────
class TermCreate(BaseModel):
    term: str
    kind: str = Field(..., pattern="^(preferred|banned)$")
    replacement: str = ""
    rule_code: str = ""

class TermUpdate(BaseModel):
    term: Optional[str] = None
    kind: Optional[str] = None
    replacement: Optional[str] = None
    rule_code: Optional[str] = None

class TermOut(BaseModel):
    id: int
    term: str
    kind: str
    replacement: str
    rule_code: str
    class Config:
        from_attributes = True


# ── Submissions ───────────────────────────────────────────────────────
class SubmissionCreate(BaseModel):
    title: str
    text: str

class SubmissionOut(BaseModel):
    id: int
    title: str
    creator_id: int
    status: str
    current_version: int
    class Config:
        from_attributes = True

class VersionOut(BaseModel):
    id: int
    submission_id: int
    version_no: int
    text: str
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# ── Findings ──────────────────────────────────────────────────────────
class FindingOut(BaseModel):
    id: int
    submission_id: int
    version_id: int
    category: str
    severity: str
    explanation: str
    source_type: str
    source_id: Optional[int]
    source_quote: str
    span_start: Optional[int]
    span_end: Optional[int]
    flagged_text: str
    verdict: str
    confidence_label: str
    confidence_score: float
    suggestion: str
    ai_generated: bool
    decision: str
    edited_text: str
    dispute_reason: str
    class Config:
        from_attributes = True

class FindingDecision(BaseModel):
    decision: str = Field(..., pattern="^(accepted|edited|disputed)$")
    edited_text: Optional[str] = None
    dispute_reason: Optional[str] = None


# ── Comments ──────────────────────────────────────────────────────────
class CommentCreate(BaseModel):
    body: str

class CommentOut(BaseModel):
    id: int
    submission_id: int
    author_id: int
    body: str
    created_at: Optional[datetime] = None
    author_name: Optional[str] = None
    class Config:
        from_attributes = True


# ── Review ────────────────────────────────────────────────────────────
class ReviewResult(BaseModel):
    submission_id: int
    version_id: int
    findings: List[FindingOut]
    ai_status: str = "available"  # available | unavailable

class ResubmitRequest(BaseModel):
    text: str

class ApproveRequest(BaseModel):
    override_reason: Optional[str] = None


# ── Insights ──────────────────────────────────────────────────────────
class InsightsOut(BaseModel):
    top_flagged_rules: list
    dispute_counts: list
    expiring_ledger: list
    total_submissions: int
    total_findings: int


# ── Disclosure ────────────────────────────────────────────────────────
class DisclosureOut(BaseModel):
    services: list
    ai_usage: str
    data_handling: str
    human_in_loop: str
    limitations: str
