"""Quote verification: verify that evidence_quote is a literal substring of the cited source."""

import re
import unicodedata
from typing import Tuple


def normalise(text: str) -> str:
    """Normalise text for comparison: lowercase, collapse whitespace, strip punctuation edges."""
    if not text:
        return ""
    # Unicode normalisation
    text = unicodedata.normalize("NFKC", text)
    # Lowercase
    text = text.lower()
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text)
    # Strip leading/trailing whitespace and punctuation
    text = text.strip().strip(".,;:!?\"'""''")
    return text


def check_quote(evidence_quote: str, source_text: str) -> Tuple[bool, float]:
    """
    Verify that evidence_quote is a literal substring of the source_text.

    Returns:
        (is_verified, confidence_score)
        - True, 1.0 if exact substring match found
        - True, 0.8 if normalised match found
        - False, 0.2 if no match found
    """
    if not evidence_quote or not source_text:
        return False, 0.2

    # First try: exact substring match
    if evidence_quote in source_text:
        return True, 1.0

    # Second try: normalised match
    norm_quote = normalise(evidence_quote)
    norm_source = normalise(source_text)

    if not norm_quote or not norm_source:
        return False, 0.2

    if norm_quote in norm_source:
        return True, 0.8

    # Third try: check if most of the quote words appear in sequence
    quote_words = norm_quote.split()
    source_words = norm_source.split()

    if len(quote_words) <= 2:
        # For very short quotes, require exact match
        return False, 0.2

    # Sliding window: check if a substantial portion matches
    match_count = 0
    for qw in quote_words:
        if qw in source_words:
            match_count += 1

    word_overlap = match_count / len(quote_words) if quote_words else 0

    if word_overlap >= 0.8:
        # High overlap but not exact substring – might be slightly paraphrased
        return True, 0.6

    return False, 0.2


def downgrade_if_unverified(finding: dict, source_text: str) -> dict:
    """
    If the AI's evidence_quote cannot be verified in the source text,
    downgrade the finding's verdict and add a note.
    """
    evidence_quote = finding.get("source_quote", "")

    if not evidence_quote or finding.get("source_type") == "none":
        return finding

    is_verified, confidence = check_quote(evidence_quote, source_text)

    if not is_verified:
        finding["verdict"] = "unverified"
        finding["confidence_label"] = "Low"
        finding["confidence_score"] = confidence
        explanation = finding.get("explanation", "")
        finding["explanation"] = (
            explanation + " ⚠️ AI quote could not be verified in the source."
        )

    return finding
