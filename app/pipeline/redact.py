"""Redaction module: mask emails, phone numbers, and configurable confidential terms."""

import re
from typing import List


# Default confidential terms to redact before sending to LLM
DEFAULT_CONFIDENTIAL_TERMS = [
    "internal", "confidential", "proprietary", "secret",
]


def redact_text(
    text: str,
    confidential_terms: List[str] | None = None,
) -> str:
    """
    Redact sensitive information from text before sending to LLM.
    Masks emails, phone numbers, and confidential terms.
    """
    redacted = text

    # Redact email addresses
    redacted = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        '[EMAIL_REDACTED]',
        redacted,
    )

    # Redact phone numbers (various formats)
    # Indian phone numbers
    redacted = re.sub(r'\b\+?91[-\s]?\d{10}\b', '[PHONE_REDACTED]', redacted)
    # General phone numbers
    redacted = re.sub(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', '[PHONE_REDACTED]', redacted)
    # Numbers starting with + followed by 10-12 digits
    redacted = re.sub(r'\+\d{10,13}\b', '[PHONE_REDACTED]', redacted)

    # Redact confidential terms
    terms = confidential_terms or DEFAULT_CONFIDENTIAL_TERMS
    for term in terms:
        pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
        redacted = pattern.sub('[REDACTED]', redacted)

    return redacted
