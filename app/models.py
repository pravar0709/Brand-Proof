"""SQLAlchemy ORM models for BrandProof."""

from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float, Date, DateTime,
    ForeignKey, CheckConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)  # creator | manager | reviewer

    submissions = relationship("Submission", back_populates="creator")
    comments = relationship("Comment", back_populates="author")


class Rule(Base):
    __tablename__ = "rules"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False)  # R1, R2, ...
    title = Column(String(200), nullable=False)
    text = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)  # tone, terminology, claims, ...
    severity = Column(String(20), nullable=False)   # high, medium, low


class LedgerEntry(Base):
    __tablename__ = "ledger"
    id = Column(Integer, primary_key=True, autoincrement=True)
    claim = Column(Text, nullable=False)
    evidence = Column(Text, nullable=False)
    allowed_wording = Column(Text, default="")
    owner = Column(String(100), default="GlowLeaf")
    expires_on = Column(String(20), nullable=True)  # ISO date string or null
    status = Column(String(20), default="active")  # active | expired


class Term(Base):
    __tablename__ = "terms"
    id = Column(Integer, primary_key=True, autoincrement=True)
    term = Column(String(100), nullable=False)
    kind = Column(String(20), nullable=False)  # preferred | banned
    replacement = Column(String(200), default="")
    rule_code = Column(String(10), default="")


class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(300), nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(30), default="draft")  # draft|in_review|changes_requested|approved
    current_version = Column(Integer, default=1)

    creator = relationship("User", back_populates="submissions")
    versions = relationship("Version", back_populates="submission", order_by="Version.version_no")
    findings = relationship("Finding", back_populates="submission")
    comments = relationship("Comment", back_populates="submission", order_by="Comment.created_at")


class Version(Base):
    __tablename__ = "versions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    version_no = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    submission = relationship("Submission", back_populates="versions")


class Finding(Base):
    __tablename__ = "findings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    version_id = Column(Integer, ForeignKey("versions.id"), nullable=False)
    category = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)  # high, medium, low
    explanation = Column(Text, nullable=False)
    source_type = Column(String(20), default="none")  # rule | ledger | none
    source_id = Column(Integer, nullable=True)
    source_quote = Column(Text, default="")
    span_start = Column(Integer, nullable=True)
    span_end = Column(Integer, nullable=True)
    flagged_text = Column(Text, default="")
    verdict = Column(String(30), nullable=False)  # supported|contradicted|outdated|unverified
    confidence_label = Column(String(20), default="Medium")  # High | Medium | Low
    confidence_score = Column(Float, default=0.5)
    suggestion = Column(Text, default="")
    ai_generated = Column(Boolean, default=False)
    decision = Column(String(20), default="pending")  # pending|accepted|edited|disputed
    edited_text = Column(Text, default="")
    dispute_reason = Column(Text, default="")

    submission = relationship("Submission", back_populates="findings")
    version = relationship("Version")


class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    submission = relationship("Submission", back_populates="comments")
    author = relationship("User", back_populates="comments")


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    actor = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    entity = Column(String(200), default="")
    detail = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
