"""Claim detection: superlatives, guarantees, medical claims – with Ledger lookup."""

import re
from typing import List, Dict, Any

# Lexicons for different claim categories
SUPERLATIVE_WORDS = [
    r"#1", r"#\d+", r"number one", r"number 1", r"best", r"world's",
    r"leading", r"top-rated", r"top rated", r"most popular", r"finest",
    r"greatest", r"unmatched", r"unrivalled", r"unparalleled",
]

GUARANTEE_WORDS = [
    r"guaranteed", r"guarantee", r"100%", r"miracle", r"forever",
    r"permanent", r"absolutely", r"always works", r"never fails",
    r"promise", r"certainty", r"without fail",
]

MEDICAL_WORDS = [
    r"clinically proven", r"clinically tested", r"cures?", r"treats?",
    r"heals?", r"prescription[- ]strength", r"doctor[- ]recommended",
    r"medically tested", r"therapeutic", r"remedy", r"anti[- ]?bacterial",
    r"prevents? disease",
]


def _build_pattern(words: List[str]) -> re.Pattern:
    """Build a combined regex pattern with word boundaries."""
    combined = "|".join(words)
    return re.compile(r'\b(' + combined + r')\b', re.IGNORECASE)


SUPERLATIVE_PATTERN = _build_pattern(SUPERLATIVE_WORDS)
GUARANTEE_PATTERN = _build_pattern(GUARANTEE_WORDS)
MEDICAL_PATTERN = _build_pattern(MEDICAL_WORDS)


def _search_ledger(matched_text: str, ledger: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    """Look for a supporting ledger entry for the matched claim text."""
    matched_lower = matched_text.lower()
    for entry in ledger:
        claim_lower = entry["claim"].lower()
        evidence_lower = entry.get("evidence", "").lower()
        allowed_lower = entry.get("allowed_wording", "").lower()
        # Check if the matched text relates to this ledger entry
        if (matched_lower in claim_lower or
            matched_lower in evidence_lower or
            matched_lower in allowed_lower):
            return entry
    return None


def check_claims(text: str, ledger: List[Dict[str, Any]], rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Check text for unsupported superlative, guarantee, and medical claims.
    For each match, search the Ledger. If no entry found, verdict=unverified.
    """
    findings = []

    checks = [
        (SUPERLATIVE_PATTERN, "claims", "R3", "superlative/ranking"),
        (GUARANTEE_PATTERN, "claims", "R2", "absolute/guarantee"),
        (MEDICAL_PATTERN, "claims", "R4", "medical/clinical"),
    ]

    for pattern, category, rule_code, claim_type in checks:
        for match in pattern.finditer(text):
            matched_text = match.group()

            # Search the ledger for supporting evidence
            ledger_entry = _search_ledger(matched_text, ledger)

            # Find the corresponding rule
            rule_obj = None
            for r in rules:
                if r["code"] == rule_code:
                    rule_obj = r
                    break

            if ledger_entry:
                # Ledger entry found – but is it active?
                if ledger_entry.get("status") == "expired":
                    verdict = "outdated"
                    explanation = (
                        f"The {claim_type} claim '{matched_text}' matches a Ledger entry, "
                        f"but it has expired (expires_on: {ledger_entry.get('expires_on', 'unknown')}). "
                        f"This claim cannot be used."
                    )
                    source_quote = ledger_entry["claim"]
                else:
                    verdict = "supported"
                    explanation = (
                        f"The {claim_type} claim '{matched_text}' is supported by "
                        f"Ledger entry: \"{ledger_entry['claim']}\""
                    )
                    source_quote = ledger_entry["claim"]

                findings.append({
                    "category": category,
                    "severity": "medium" if verdict == "supported" else "high",
                    "explanation": explanation,
                    "source_type": "ledger",
                    "source_id": ledger_entry.get("id"),
                    "source_quote": source_quote,
                    "span_start": match.start(),
                    "span_end": match.end(),
                    "flagged_text": matched_text,
                    "verdict": verdict,
                    "confidence_label": "High",
                    "confidence_score": 1.0,
                    "suggestion": f"Remove the {claim_type} claim '{matched_text}' (expired)" if verdict == "outdated"
                        else f"Ensure '{matched_text}' matches approved wording: \"{ledger_entry.get('allowed_wording', '')}\"",
                    "ai_generated": False,
                })
            else:
                # No ledger entry – unverified
                source_quote = rule_obj["text"] if rule_obj else ""
                findings.append({
                    "category": category,
                    "severity": "high",
                    "explanation": (
                        f"The {claim_type} claim '{matched_text}' has no approved source in the Claim Ledger. "
                        f"No approved source supports this claim. "
                        f"See rule {rule_code}: {rule_obj['title'] if rule_obj else 'N/A'}."
                    ),
                    "source_type": "rule" if rule_obj else "none",
                    "source_id": rule_obj.get("id") if rule_obj else None,
                    "source_quote": source_quote,
                    "span_start": match.start(),
                    "span_end": match.end(),
                    "flagged_text": matched_text,
                    "verdict": "unverified",
                    "confidence_label": "High",
                    "confidence_score": 1.0,
                    "suggestion": f"Remove the unsupported {claim_type} claim '{matched_text}' or add it to the Claim Ledger with evidence",
                    "ai_generated": False,
                })

    return findings
