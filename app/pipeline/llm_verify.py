"""LLM verification wrapper with quote checking and confidence calibration."""

from typing import List, Dict, Any, Optional
from app.pipeline.llm import verify_claim
from app.pipeline.quote_check import check_quote, downgrade_if_unverified


async def llm_verify_finding(
    sentence: str,
    sources: List[Dict[str, Any]],
    source_texts: Dict[int, str],
) -> tuple[Optional[Dict[str, Any]], str]:
    """
    Run LLM verification for a sentence, then quote-check the result.

    Args:
        sentence: The sentence to verify
        sources: Retrieved source documents
        source_texts: Map of source_id -> full source text for quote verification

    Returns:
        (finding_dict or None, ai_status)
    """
    result, ai_status = await verify_claim(sentence, sources)

    if result is None:
        return None, ai_status

    # Build finding dict from LLM result
    source_id = result.get("source_id")
    source_type = "none"
    source_quote = result.get("evidence_quote", "")

    # Determine source type
    if source_id is not None:
        for src in sources:
            if str(src.get("id")) == str(source_id):
                source_type = src.get("type", "none")
                break

    finding = {
        "category": "claims",
        "severity": "medium",
        "explanation": result.get("explanation", ""),
        "source_type": source_type,
        "source_id": int(source_id) if source_id and str(source_id).isdigit() else None,
        "source_quote": source_quote,
        "flagged_text": sentence,
        "verdict": result.get("verdict", "unverified"),
        "confidence_score": float(result.get("confidence", 0.5)),
        "suggestion": result.get("suggestion", ""),
        "ai_generated": True,
    }

    # Quote check: verify the evidence_quote is in the source text
    if source_id and str(source_id) in source_texts:
        source_full_text = source_texts[str(source_id)]
        finding = downgrade_if_unverified(finding, source_full_text)
    elif source_id is not None:
        # Source ID given but we don't have the text – can't verify
        finding["verdict"] = "unverified"
        finding["confidence_label"] = "Low"
        finding["confidence_score"] = 0.3
        finding["explanation"] += " ⚠️ Source could not be located for quote verification."

    # Confidence label calibration
    # LLM findings capped at Medium unless quote check passes
    score = finding["confidence_score"]
    if finding["ai_generated"]:
        if score >= 0.8 and finding.get("verdict") != "unverified":
            finding["confidence_label"] = "Medium"  # Capped at Medium for LLM
        elif score >= 0.5:
            finding["confidence_label"] = "Medium"
        else:
            finding["confidence_label"] = "Low"
    else:
        if score >= 0.8:
            finding["confidence_label"] = "High"
        elif score >= 0.5:
            finding["confidence_label"] = "Medium"
        else:
            finding["confidence_label"] = "Low"

    return finding, ai_status
