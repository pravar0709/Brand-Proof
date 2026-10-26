"""Database engine, session, table creation, and seeding."""

import os
import json
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///brandproof.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

# Enable WAL mode for better concurrency
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency – yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables from ORM models."""
    from app.models import Base
    Base.metadata.create_all(bind=engine)


def seed_database():
    """Seed users + brand data from JSON (idempotent)."""
    from app.models import User, Rule, LedgerEntry, Term
    db = SessionLocal()
    try:
        # Seed users (idempotent)
        existing = db.query(User).count()
        if existing == 0:
            users = [
                User(id=1, name="Asha", role="creator"),
                User(id=2, name="Meera", role="manager"),
                User(id=3, name="Rohan", role="reviewer"),
            ]
            db.add_all(users)
            db.commit()

        # Seed brand data from JSON (idempotent)
        if db.query(Rule).count() == 0:
            seed_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "seed", "skincare_brand.json"
            )
            if os.path.exists(seed_path):
                with open(seed_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for r in data.get("rules", []):
                    db.add(Rule(
                        code=r["code"], title=r["title"], text=r["text"],
                        category=r["category"], severity=r["severity"]
                    ))

                for le in data.get("ledger", []):
                    db.add(LedgerEntry(
                        claim=le["claim"], evidence=le["evidence"],
                        allowed_wording=le.get("allowed_wording", ""),
                        owner=le.get("owner", "GlowLeaf"),
                        expires_on=le.get("expires_on"),
                        status=le.get("status", "active"),
                    ))

                for t in data.get("terms", []):
                    db.add(Term(
                        term=t["term"], kind=t["kind"],
                        replacement=t.get("replacement", ""),
                        rule_code=t.get("rule_code", ""),
                    ))

                db.commit()
    finally:
        db.close()
