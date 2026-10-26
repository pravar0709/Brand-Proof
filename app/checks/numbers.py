"""Number extraction and Ledger comparison check."""

import re
from typing import List, Dict, Any

# Pattern to match numbers with units commonly found in skincare copy
NUMBER_PATTERNS = [
    # SPF values
    (re.compile(r'\bSPF\s*(\d+)\b', re.IGNORECASE), "SPF"),
    # Duration: X hours/minutes
    (re.compile(r'\b(\d+)\s*hours?\b', re.IGNORECASE), "hours"),
    (re.compile(r'\b(\d+)\s*minutes?\b', re.IGNORECASE), "minutes"),
    # Percentages
    (re.compile(r'\b(\d+(?:\.\d+)?)\s*%', re.IGNORECASE), "%"),
    # Currency: Rs/INR amounts
    (re.compile(r'\bRs\.?\s*(\d+(?:,\d+)*)\b', re.IGNORECASE), "Rs"),
    (re.compile(r'\bINR\s*(\d+(?:,\d+)*)\b', re.IGNORECASE), "Rs"),
    # Volunteers/people count
    (re.compile(r'\b(\d+)\s*volunteers?\b', re.IGNORECASE), "volunteers"),
]


def _extract_numbers_from_text(text: str) -> List[Dict[str, Any]]:
    """Extract all number+unit pairs from text."""
    results = []
    for pattern, unit in NUMBER_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1).replace(",", "")
            results.append({
                "value": value,
                "unit": unit,
                "full_match": match.group(0),
                "start": match.start(),
                "end": match.end(),
            })
    return results


def _find_contradictions(number_info: Dict, ledger: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Check if a number contradicts any ledger entry."""
    contradictions = []
    value = number_info["value"]
    unit = number_info["unit"]

    for entry in ledger:
        entry_text = f"{entry['claim']} {entry.get('evidence', '')} {entry.get('allowed_wording', '')}"

        # Extract numbers from the ledger entry for comparison
        for pattern, l_unit in NUMBER_PATTERNS:
            if l_unit != unit:
                continue
            for l_match in pattern.finditer(entry_text):
                l_value = l_match.group(1).replace(",", "")

                # Same unit, different value => contradiction
                if l_unit == unit and l_value != value:
                    # Special case: "12 hours" vs "2 hours" (reapply context)
                    contradictions.append({
                        "ledger_entry": entry,
                        "ledger_value": l_value,
                        "ledger_unit": l_unit,
                        "ledger_text": l_match.group(0),
                    })

    return contradictions


def check_numbers(text: str, ledger: List[Dict[str, Any]], rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract numbers+units from text, compare to Ledger.
    Mismatch => verdict=contradicted with citation.
    """
    findings = []
    numbers = _extract_numbers_from_text(text)

    for num_info in numbers:
        contradictions = _find_contradictions(num_info, ledger)

        for contra in contradictions:
            entry = contra["ledger_entry"]
            findings.append({
                "category": "claims",
                "severity": "high",
                "explanation": (
                    f"Number mismatch: the text says '{num_info['full_match']}' but the "
                    f"Claim Ledger states '{contra['ledger_text']}' "
                    f"(Ledger entry: \"{entry['claim']}\"). These values contradict each other."
                ),
                "source_type": "ledger",
                "source_id": entry.get("id"),
                "source_quote": entry["claim"] + ". " + entry.get("evidence", ""),
                "span_start": num_info["start"],
                "span_end": num_info["end"],
                "flagged_text": num_info["full_match"],
                "verdict": "contradicted",
                "confidence_label": "High",
                "confidence_score": 1.0,
                "suggestion": f"Change '{num_info['full_match']}' to match the approved Ledger value '{contra['ledger_text']}'",
                "ai_generated": False,
            })

    return findings
