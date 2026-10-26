"""Readability checks: sentence length (R12), sunscreen reapply rule (R5)."""

import re
from typing import List, Dict, Any


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences, handling common edge cases."""
    # Split on period, exclamation, question mark followed by space or end
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def check_readability(text: str, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """R12: Check average sentence length (under 25 words)."""
    findings = []
    sentences = _split_sentences(text)

    if not sentences:
        return findings

    word_counts = [len(s.split()) for s in sentences]
    avg_length = sum(word_counts) / len(word_counts)

    if avg_length > 25:
        rule_obj = next((r for r in rules if r["code"] == "R12"), None)
        findings.append({
            "category": "formatting",
            "severity": "low",
            "explanation": (
                f"Average sentence length is {avg_length:.1f} words (limit: 25). "
                f"R12: Keep sentences concise for readability, especially on mobile."
            ),
            "source_type": "rule",
            "source_id": rule_obj.get("id") if rule_obj else None,
            "source_quote": rule_obj["text"] if rule_obj else "",
            "span_start": 0,
            "span_end": len(text),
            "flagged_text": text[:100] + "..." if len(text) > 100 else text,
            "verdict": "contradicted",
            "confidence_label": "High",
            "confidence_score": 0.8,
            "suggestion": "Break up long sentences into shorter ones (aim for under 25 words each).",
            "ai_generated": False,
        })

    return findings


def check_sunscreen_reapply(text: str, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """R5: Sunscreen/SPF mention must include 'reapply every 2 hours'."""
    findings = []
    text_lower = text.lower()

    # Check if text mentions sunscreen or SPF
    has_sunscreen = bool(re.search(r'\b(sunscreen|spf|sun protection)\b', text_lower))

    if not has_sunscreen:
        return findings

    # Check if it includes the reapply reminder
    has_reapply = bool(re.search(r'\breapply\b', text_lower))

    if not has_reapply:
        rule_obj = next((r for r in rules if r["code"] == "R5"), None)
        # Find the sunscreen mention position
        match = re.search(r'\b(sunscreen|spf\s*\d*|sun protection)\b', text, re.IGNORECASE)
        span_start = match.start() if match else 0
        span_end = match.end() if match else len(text)

        findings.append({
            "category": "claims",
            "severity": "high",
            "explanation": (
                f"Sunscreen/SPF content found but missing the required 'reapply every 2 hours' reminder. "
                f"R5: Any content mentioning sunscreen or SPF must always include this safety reminder."
            ),
            "source_type": "rule",
            "source_id": rule_obj.get("id") if rule_obj else None,
            "source_quote": rule_obj["text"] if rule_obj else "",
            "span_start": span_start,
            "span_end": span_end,
            "flagged_text": match.group() if match else "sunscreen/SPF",
            "verdict": "contradicted",
            "confidence_label": "High",
            "confidence_score": 1.0,
            "suggestion": "Add 'Reapply every 2 hours for continued protection.' to the text.",
            "ai_generated": False,
        })

    return findings
