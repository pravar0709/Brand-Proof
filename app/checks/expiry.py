"""Expiry check: flag claims matching expired Ledger entries."""

import re
from datetime import date, datetime
from typing import List, Dict, Any


def check_expiry(text: str, ledger: List[Dict[str, Any]], rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    If text matches a Ledger entry whose expires_on < today => verdict=outdated.
    """
    findings = []
    text_lower = text.lower()
    today = date.today()

    for entry in ledger:
        expires_on = entry.get("expires_on")
        if not expires_on:
            continue

        # Parse expiry date
        try:
            expiry_date = datetime.strptime(expires_on, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue

        if expiry_date >= today:
            continue  # Not expired

        # Check if text references this expired entry
        claim_lower = entry["claim"].lower()
        # Extract key phrases from the claim to search in text
        claim_words = claim_lower.split()

        # Try to find a substantial match (at least 3 consecutive words)
        matched = False
        match_start = -1
        match_end = -1
        matched_text = ""

        # Try progressively shorter n-grams from the claim
        for n in range(len(claim_words), 2, -1):
            for i in range(len(claim_words) - n + 1):
                phrase = " ".join(claim_words[i:i+n])
                idx = text_lower.find(phrase)
                if idx >= 0:
                    matched = True
                    match_start = idx
                    match_end = idx + len(phrase)
                    matched_text = text[match_start:match_end]
                    break
            if matched:
                break

        if not matched:
            # Try individual significant keywords (>4 chars)
            for word in claim_words:
                if len(word) > 4:
                    pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
                    m = pattern.search(text)
                    if m:
                        # Check if enough context matches
                        pass  # Single word match is too loose, skip

        if matched:
            findings.append({
                "category": "claims",
                "severity": "high",
                "explanation": (
                    f"This text references an expired Claim Ledger entry: "
                    f"\"{entry['claim']}\". "
                    f"The entry expired on {expires_on}. "
                    f"This claim should be removed or updated."
                ),
                "source_type": "ledger",
                "source_id": entry.get("id"),
                "source_quote": f"{entry['claim']} (expired: {expires_on})",
                "span_start": match_start,
                "span_end": match_end,
                "flagged_text": matched_text,
                "verdict": "outdated",
                "confidence_label": "High",
                "confidence_score": 1.0,
                "suggestion": f"Remove the expired claim '{matched_text}' or update the Ledger entry with a new valid date",
                "ai_generated": False,
            })

    return findings
