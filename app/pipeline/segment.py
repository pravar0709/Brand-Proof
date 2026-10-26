"""Text segmentation for the review pipeline."""

import re
from typing import List, Dict


def segment_text(text: str) -> List[Dict]:
    """
    Split text into sentences with positions.
    Returns list of dicts: {text, start, end, has_claim}
    """
    segments = []

    # Split on sentence boundaries
    sentence_pattern = re.compile(r'[^.!?\n]+[.!?\n]*')
    for match in sentence_pattern.finditer(text):
        sentence = match.group().strip()
        if not sentence:
            continue

        # Determine if this sentence likely contains a checkable claim
        has_claim = bool(re.search(
            r'\b(\d+|spf|proven|tested|certified|free|resistant|approved|'
            r'best|#\d|guaranteed|miracle|clinically|dermatologist|'
            r'organic|natural|vegan|cruelty|recyclable|shipping)\b',
            sentence, re.IGNORECASE
        ))

        segments.append({
            "text": sentence,
            "start": match.start(),
            "end": match.end(),
            "has_claim": has_claim,
        })

    return segments
