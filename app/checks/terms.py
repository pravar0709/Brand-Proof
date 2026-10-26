"""Banned/preferred term detection with word-boundary matching."""

import re
from typing import List, Dict, Any


def check_terms(text: str, terms: List[Dict[str, Any]], rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Check text for banned/preferred term usage.
    Returns a list of finding dicts.
    """
    findings = []
    text_lower = text.lower()

    for term_entry in terms:
        term = term_entry["term"]
        kind = term_entry["kind"]

        if kind != "banned":
            continue

        # Word-boundary match, case-insensitive
        pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
        for match in pattern.finditer(text):
            # Find the rule that corresponds to this term
            rule_code = term_entry.get("rule_code", "")
            source_quote = ""
            source_id = None
            rule_obj = None

            if rule_code:
                for r in rules:
                    if r["code"] == rule_code:
                        rule_obj = r
                        source_quote = r["text"]
                        source_id = r.get("id")
                        break

            replacement = term_entry.get("replacement", "")
            suggestion = ""
            if replacement:
                # Build a suggestion by replacing the matched term
                suggestion = text[max(0, match.start()-20):match.start()] + replacement + text[match.end():match.end()+20]
                suggestion = suggestion.strip()
            explanation = f"Banned term '{match.group()}' found."
            if replacement:
                explanation += f" Use '{replacement}' instead."
            if rule_code:
                explanation += f" See rule {rule_code}."

            findings.append({
                "category": "terminology",
                "severity": rule_obj["severity"] if rule_obj else "medium",
                "explanation": explanation,
                "source_type": "rule" if rule_code else "none",
                "source_id": source_id,
                "source_quote": source_quote,
                "span_start": match.start(),
                "span_end": match.end(),
                "flagged_text": match.group(),
                "verdict": "contradicted",
                "confidence_label": "High",
                "confidence_score": 1.0,
                "suggestion": f"Replace '{match.group()}' with '{replacement}'" if replacement else f"Remove or rephrase '{match.group()}'",
                "ai_generated": False,
            })

    return findings
