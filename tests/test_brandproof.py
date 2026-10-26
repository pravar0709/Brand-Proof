"""Comprehensive tests for BrandProof – at least 15 tests covering all key features."""

import os
import sys
import json
import pytest
from unittest.mock import patch, AsyncMock
from datetime import date, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    """Create a fresh app with test database."""
    # Use in-memory SQLite for tests
    os.environ["DATABASE_URL"] = "sqlite:///test_brandproof.db"
    os.environ["LLM_PROVIDER"] = "none"

    from app.main import app as fastapi_app
    from app.db import create_tables, seed_database, engine
    from app.models import Base

    Base.metadata.drop_all(bind=engine)
    create_tables()
    seed_database()

    yield fastapi_app

    # Cleanup
    try:
        os.remove("test_brandproof.db")
    except OSError:
        pass


@pytest.fixture(scope="module")
def client(app):
    return TestClient(app)


@pytest.fixture(scope="module")
def creator_token(client):
    resp = client.post("/api/auth/demo", json={"role": "creator"})
    assert resp.status_code == 200
    return resp.json()["token"]


@pytest.fixture(scope="module")
def manager_token(client):
    resp = client.post("/api/auth/demo", json={"role": "manager"})
    assert resp.status_code == 200
    return resp.json()["token"]


@pytest.fixture(scope="module")
def reviewer_token(client):
    resp = client.post("/api/auth/demo", json={"role": "reviewer"})
    assert resp.status_code == 200
    return resp.json()["token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ── Load seed data for reference ──────────────────────────────────────

def load_seed():
    seed_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seed", "skincare_brand.json")
    with open(seed_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ══════════════════════════════════════════════════════════════════════
# TESTS
# ══════════════════════════════════════════════════════════════════════


# 1. Banned term detection
def test_banned_term_detection():
    """Banned terms (e.g., 'sun block') should be detected with word-boundary matching."""
    from app.checks.terms import check_terms

    seed = load_seed()
    text = "Try our amazing sun block for summer protection"
    findings = check_terms(text, seed["terms"], seed["rules"])

    assert len(findings) >= 1
    banned_found = [f for f in findings if "sun block" in f["flagged_text"].lower()]
    assert len(banned_found) >= 1
    assert banned_found[0]["verdict"] == "contradicted"
    assert banned_found[0]["source_type"] == "rule"


# 2. Superlative with no ledger entry => unverified
def test_superlative_no_ledger_entry():
    """'#1 sunscreen' should be unverified since no ledger entry supports it."""
    from app.checks.claims import check_claims

    seed = load_seed()
    text = "#1 sunscreen in India!"
    findings = check_claims(text, seed["ledger"], seed["rules"])

    superlative = [f for f in findings if f["verdict"] == "unverified" and "#1" in f["flagged_text"]]
    assert len(superlative) >= 1
    assert "No approved source" in superlative[0]["explanation"]


# 3. Number mismatch => contradicted with citation
def test_number_mismatch_contradicted():
    """'12 hours' should contradict the Ledger's '2 hours' reapply requirement."""
    from app.checks.numbers import check_numbers

    seed = load_seed()
    text = "SPF 50 for 12 hours of protection"
    findings = check_numbers(text, seed["ledger"], seed["rules"])

    hour_findings = [f for f in findings if "hours" in f["flagged_text"].lower() and f["verdict"] == "contradicted"]
    assert len(hour_findings) >= 1
    assert "Ledger" in hour_findings[0]["explanation"] or "ledger" in hour_findings[0]["explanation"].lower()


# 4. Expired ledger entry => outdated
def test_expired_ledger_outdated():
    """Reference to expired free shipping offer should be flagged as outdated."""
    from app.checks.expiry import check_expiry

    seed = load_seed()
    text = "Free shipping across India on orders above Rs 499"
    findings = check_expiry(text, seed["ledger"], seed["rules"])

    outdated = [f for f in findings if f["verdict"] == "outdated"]
    assert len(outdated) >= 1
    assert "expired" in outdated[0]["explanation"].lower()


# 5. Hashtag casing check
def test_hashtag_casing():
    """All-lowercase hashtags should be flagged for accessibility."""
    from app.checks.tone_rules import _check_hashtag_casing

    seed = load_seed()
    text = "Check out our new product #glowleaf #bestsunscreen"
    findings = _check_hashtag_casing(text, seed["rules"])

    assert len(findings) >= 1
    lowercase_tags = [f for f in findings if "lowercase" in f["explanation"].lower() or "CamelCase" in f["explanation"]]
    assert len(lowercase_tags) >= 1


# 6. R5 sunscreen reapply rule
def test_sunscreen_reapply_rule():
    """SPF mention without 'reapply' should trigger R5 finding."""
    from app.checks.readability import check_sunscreen_reapply

    seed = load_seed()
    text = "Our SPF 50 sunscreen provides all-day protection"
    findings = check_sunscreen_reapply(text, seed["rules"])

    assert len(findings) >= 1
    assert findings[0]["verdict"] == "contradicted"
    assert "reapply" in findings[0]["explanation"].lower()


# 7. Emoji limit check
def test_emoji_limit():
    """More than 2 emojis should be flagged."""
    from app.checks.tone_rules import _check_emoji_count

    seed = load_seed()
    text = "Amazing product! \U0001f31e\U0001f525\u2728 Love it!"
    findings = _check_emoji_count(text, seed["rules"])

    assert len(findings) >= 1
    assert "emoji" in findings[0]["explanation"].lower()


# 8. Quote check passes on literal quote
def test_quote_check_literal_pass():
    """Quote check should pass when the quote is a literal substring of the source."""
    from app.pipeline.quote_check import check_quote

    source = "SPF 50 protection with broad-spectrum UVA/UVB coverage. Reapply every 2 hours."
    quote = "Reapply every 2 hours"
    is_verified, confidence = check_quote(quote, source)

    assert is_verified is True
    assert confidence >= 0.8


# 9. Quote check downgrades a fabricated quote
def test_quote_check_fabricated_downgrade():
    """Quote check should fail when the quote is fabricated."""
    from app.pipeline.quote_check import check_quote

    source = "SPF 50 protection with broad-spectrum UVA/UVB coverage."
    quote = "Clinically proven to cure all skin conditions and prevent aging"
    is_verified, confidence = check_quote(quote, source)

    assert is_verified is False
    assert confidence <= 0.3


# 10. Redact masks emails and phones
def test_redact_masks_emails_phones():
    """Redaction should mask email addresses and phone numbers."""
    from app.pipeline.redact import redact_text

    text = "Contact us at hello@glowleaf.com or call +919876543210 for details"
    redacted = redact_text(text)

    assert "hello@glowleaf.com" not in redacted
    assert "[EMAIL_REDACTED]" in redacted
    assert "9876543210" not in redacted


# 11. LLM-failure fallback still returns deterministic findings
def test_llm_failure_fallback(client, creator_token):
    """When LLM is unavailable, deterministic findings should still be returned."""
    # Create submission with known bad content
    resp = client.post(
        "/api/submissions",
        json={"title": "Test LLM Fallback", "text": "#1 sunscreen guaranteed miracle cure #glowleaf"},
        headers=auth_header(creator_token),
    )
    assert resp.status_code == 200
    sub_id = resp.json()["id"]

    # Run review (LLM_PROVIDER=none)
    resp = client.post(
        f"/api/submissions/{sub_id}/review",
        headers=auth_header(creator_token),
    )
    assert resp.status_code == 200
    result = resp.json()

    assert result["findings_count"] >= 1
    # Should have some findings even without LLM
    findings = result["findings"]
    assert len(findings) >= 1


# 12. Role guard: creator cannot approve
def test_creator_cannot_approve(client, creator_token):
    """Creators should not be able to approve submissions."""
    # Try to approve submission 1 as creator
    resp = client.post(
        "/api/submissions/1/approve",
        headers=auth_header(creator_token),
    )
    assert resp.status_code == 403


# 13. Approval blocked with pending findings
def test_approval_blocked_pending_findings(client, creator_token, reviewer_token):
    """Reviewer cannot approve if findings are still pending (without override)."""
    # Create submission with content that will generate findings
    resp = client.post(
        "/api/submissions",
        json={"title": "Test Pending Block", "text": "Guaranteed miracle sunscreen #1 in India!"},
        headers=auth_header(creator_token),
    )
    sub_id = resp.json()["id"]

    # Run review
    client.post(f"/api/submissions/{sub_id}/review", headers=auth_header(creator_token))

    # Try to approve without override
    resp = client.post(
        f"/api/submissions/{sub_id}/approve",
        headers=auth_header(reviewer_token),
    )
    assert resp.status_code == 400
    assert "pending" in resp.json()["detail"].lower()


# 14. Dispute requires reason
def test_dispute_requires_reason(client, creator_token):
    """Disputing a finding should require a reason."""
    # Create a submission and review it
    resp = client.post(
        "/api/submissions",
        json={"title": "Test Dispute", "text": "Guaranteed results with our miracle formula!"},
        headers=auth_header(creator_token),
    )
    sub_id = resp.json()["id"]

    resp = client.post(f"/api/submissions/{sub_id}/review", headers=auth_header(creator_token))
    findings = resp.json()["findings"]

    if findings:
        finding_id = findings[0]["id"]
        # Try to dispute without reason
        resp = client.post(
            f"/api/findings/{finding_id}/decision",
            json={"decision": "disputed"},
            headers=auth_header(creator_token),
        )
        assert resp.status_code == 400


# 15. Version increments on resubmit
def test_version_increments_on_resubmit(client, creator_token):
    """Resubmitting should create a new version with incremented version number."""
    # Create submission
    resp = client.post(
        "/api/submissions",
        json={"title": "Test Versioning", "text": "Original text for versioning test"},
        headers=auth_header(creator_token),
    )
    sub_id = resp.json()["id"]
    assert resp.json()["current_version"] == 1

    # Run initial review
    client.post(f"/api/submissions/{sub_id}/review", headers=auth_header(creator_token))

    # Resubmit with new text
    resp = client.post(
        f"/api/submissions/{sub_id}/resubmit",
        json={"text": "Improved text for versioning test"},
        headers=auth_header(creator_token),
    )
    assert resp.status_code == 200
    assert resp.json()["version_no"] == 2


# 16. Clean draft yields no high-severity findings
def test_clean_draft_few_findings(client, creator_token):
    """A clean, compliant draft should produce few or no high-severity findings."""
    clean_text = (
        "Discover our GlowLeaf niacinamide serum with 2% niacinamide for smoother, "
        "brighter skin. Dermatologist-tested and fragrance-free. "
        "Gentle enough for sensitive skin. #GlowLeafSkincare"
    )

    resp = client.post(
        "/api/submissions",
        json={"title": "Clean Draft Test", "text": clean_text},
        headers=auth_header(creator_token),
    )
    sub_id = resp.json()["id"]

    resp = client.post(f"/api/submissions/{sub_id}/review", headers=auth_header(creator_token))
    findings = resp.json()["findings"]

    high_severity = [f for f in findings if f["severity"] == "high"]
    # Clean draft should have very few high-severity findings
    assert len(high_severity) <= 2


# 17. Health check endpoint
def test_health_check(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# 18. Demo login and me endpoint
def test_demo_login_and_me(client):
    resp = client.post("/api/auth/demo", json={"role": "creator"})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["user"]["role"] == "creator"
    assert data["user"]["name"] == "Asha"

    # Test /api/me
    me_resp = client.get("/api/me", headers=auth_header(data["token"]))
    assert me_resp.status_code == 200
    assert me_resp.json()["role"] == "creator"


# 19. Samples endpoint returns drafts
def test_samples_endpoint(client):
    resp = client.get("/api/samples")
    assert resp.status_code == 200
    data = resp.json()
    assert "drafts" in data
    assert len(data["drafts"]) >= 3


# 20. Medical claim without ledger entry
def test_medical_claim_unverified():
    """'Clinically proven' with no ledger support should be unverified."""
    from app.checks.claims import check_claims

    seed = load_seed()
    text = "Clinically proven to improve skin texture"
    findings = check_claims(text, seed["ledger"], seed["rules"])

    medical = [f for f in findings if "clinically proven" in f["flagged_text"].lower()]
    assert len(medical) >= 1
    assert medical[0]["verdict"] == "unverified"


# 21. Guarantee word detection
def test_guarantee_word_detection():
    """'Guaranteed' should be detected as absolute/guarantee language."""
    from app.checks.claims import check_claims

    seed = load_seed()
    text = "Guaranteed to stop tanning with our sunscreen"
    findings = check_claims(text, seed["ledger"], seed["rules"])

    guarantee = [f for f in findings if "guaranteed" in f["flagged_text"].lower()]
    assert len(guarantee) >= 1


# 22. Disclosure endpoint
def test_disclosure_endpoint(client, creator_token):
    resp = client.get("/api/disclosure")
    assert resp.status_code == 200
    data = resp.json()
    assert "services" in data
    assert "human_in_loop" in data
    assert "limitations" in data
