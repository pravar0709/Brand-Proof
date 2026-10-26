"""Tone rule checks: exclamation density, ALL CAPS, fear/aggressive words, emoji count, hashtag casing."""

import re
from typing import List, Dict, Any

# Fear/aggressive word list (R13, R1)
FEAR_WORDS = [
    "dangerous", "toxic", "poison", "poisonous", "harmful chemicals",
    "skin damage", "aging skin", "wrinkles will worsen", "destroy",
    "devastate", "ruin", "terrifying", "scary", "alarming",
    "warning", "beware", "threat",
]

AGGRESSIVE_WORDS = [
    "crush", "dominate", "destroy", "obliterate", "annihilate",
    "kill", "slay", "smash", "blast", "attack",
]


def _check_exclamation_density(text: str, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """R1: Check exclamation mark density."""
    findings = []
    excl_count = text.count("!")
    # Split by paragraphs
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    if excl_count > len(paragraphs):
        rule_obj = next((r for r in rules if r["code"] == "R1"), None)
        findings.append({
            "category": "tone",
            "severity": "medium",
            "explanation": (
                f"Excessive exclamation marks: {excl_count} found "
                f"(max 1 per paragraph, {len(paragraphs)} paragraph(s)). "
                f"See R1: Brand voice should be friendly and factual, not aggressive."
            ),
            "source_type": "rule",
            "source_id": rule_obj.get("id") if rule_obj else None,
            "source_quote": rule_obj["text"] if rule_obj else "",
            "span_start": text.find("!"),
            "span_end": text.find("!") + 1,
            "flagged_text": "!" * excl_count,
            "verdict": "contradicted",
            "confidence_label": "High",
            "confidence_score": 0.9,
            "suggestion": "Reduce exclamation marks to at most 1 per paragraph. Use periods for a calmer, more factual tone.",
            "ai_generated": False,
        })
    return findings


def _check_all_caps(text: str, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """R1: Flag ALL CAPS words (3+ letters)."""
    findings = []
    caps_pattern = re.compile(r'\b([A-Z]{3,})\b')
    # Exclude common abbreviations
    exclude = {"SPF", "UV", "UVA", "UVB", "USA", "UK", "NABL", "FDA", "IFRA", "HDPE", "INR"}

    for match in caps_pattern.finditer(text):
        word = match.group(1)
        if word in exclude:
            continue
        rule_obj = next((r for r in rules if r["code"] == "R1"), None)
        findings.append({
            "category": "tone",
            "severity": "low",
            "explanation": (
                f"ALL CAPS word '{word}' found. "
                f"R1: Never use ALL CAPS for emphasis. Use normal casing instead."
            ),
            "source_type": "rule",
            "source_id": rule_obj.get("id") if rule_obj else None,
            "source_quote": rule_obj["text"] if rule_obj else "",
            "span_start": match.start(),
            "span_end": match.end(),
            "flagged_text": word,
            "verdict": "contradicted",
            "confidence_label": "High",
            "confidence_score": 0.95,
            "suggestion": f"Change '{word}' to normal casing",
            "ai_generated": False,
        })
    return findings


def _check_fear_language(text: str, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """R13: Check for fear-based language."""
    findings = []
    text_lower = text.lower()
    rule_obj = next((r for r in rules if r["code"] == "R13"), None)

    for word in FEAR_WORDS + AGGRESSIVE_WORDS:
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        for match in pattern.finditer(text):
            findings.append({
                "category": "tone",
                "severity": "high",
                "explanation": (
                    f"Fear/aggressive language detected: '{match.group()}'. "
                    f"R13: Avoid fear-based or anxiety-inducing language. "
                    f"Focus on positive outcomes instead."
                ),
                "source_type": "rule",
                "source_id": rule_obj.get("id") if rule_obj else None,
                "source_quote": rule_obj["text"] if rule_obj else "",
                "span_start": match.start(),
                "span_end": match.end(),
                "flagged_text": match.group(),
                "verdict": "contradicted",
                "confidence_label": "High",
                "confidence_score": 0.9,
                "suggestion": f"Replace '{match.group()}' with positive language focusing on benefits",
                "ai_generated": False,
            })
    return findings


def _check_emoji_count(text: str, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """R9: Max 2 emojis per post."""
    findings = []
    # Match emoji ranges (simplified but covers most common emojis)
    emoji_pattern = re.compile(
        "[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0000FE00-\U0000FEFF"
        "\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002702-\U000027B0"
        "\U0000200D\U00002049\U0000203C]+",
        re.UNICODE,
    )
    emojis = emoji_pattern.findall(text)
    # Count individual emojis (each character in the matches)
    emoji_chars = []
    for e in emojis:
        emoji_chars.extend(list(e))
    # Filter to actual emoji characters only
    actual_emojis = [c for c in emoji_chars if ord(c) > 0x2000]

    if len(actual_emojis) > 2:
        rule_obj = next((r for r in rules if r["code"] == "R9"), None)
        findings.append({
            "category": "formatting",
            "severity": "medium",
            "explanation": (
                f"Too many emojis: {len(actual_emojis)} found (maximum 2 per post). "
                f"R9: Use a maximum of 2 emojis per social media post."
            ),
            "source_type": "rule",
            "source_id": rule_obj.get("id") if rule_obj else None,
            "source_quote": rule_obj["text"] if rule_obj else "",
            "span_start": 0,
            "span_end": len(text),
            "flagged_text": "".join(actual_emojis),
            "verdict": "contradicted",
            "confidence_label": "High",
            "confidence_score": 1.0,
            "suggestion": f"Reduce emojis to 2 or fewer. Currently using {len(actual_emojis)}.",
            "ai_generated": False,
        })
    return findings


def _check_hashtag_casing(text: str, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """R8: Hashtags must use CamelCase for screen reader accessibility."""
    findings = []
    hashtag_pattern = re.compile(r'#([a-zA-Z]\w+)')
    rule_obj = next((r for r in rules if r["code"] == "R8"), None)

    for match in hashtag_pattern.finditer(text):
        tag = match.group(1)
        # Check if it's all lowercase
        if tag == tag.lower() and len(tag) > 1:
            findings.append({
                "category": "accessibility",
                "severity": "medium",
                "explanation": (
                    f"Hashtag '#{tag}' is all lowercase. "
                    f"R8: Use CamelCase for hashtags (e.g., #GlowLeaf) for screen reader accessibility."
                ),
                "source_type": "rule",
                "source_id": rule_obj.get("id") if rule_obj else None,
                "source_quote": rule_obj["text"] if rule_obj else "",
                "span_start": match.start(),
                "span_end": match.end(),
                "flagged_text": "#" + tag,
                "verdict": "contradicted",
                "confidence_label": "High",
                "confidence_score": 1.0,
                "suggestion": f"Change '#{tag}' to CamelCase, e.g., #{''.join(w.capitalize() for w in re.split(r'(?=[A-Z])|_', tag) if w)}",
                "ai_generated": False,
            })
    return findings


def check_tone_rules(text: str, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run all tone/formatting rule checks."""
    findings = []
    findings.extend(_check_exclamation_density(text, rules))
    findings.extend(_check_all_caps(text, rules))
    findings.extend(_check_fear_language(text, rules))
    findings.extend(_check_emoji_count(text, rules))
    findings.extend(_check_hashtag_casing(text, rules))
    return findings
