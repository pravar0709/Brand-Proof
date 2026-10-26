"""Review pipeline orchestrator – the heart of BrandProof."""

import logging
from typing import List, Dict, Any

from app.checks.terms import check_terms
from app.checks.claims import check_claims
from app.checks.numbers import check_numbers
from app.checks.expiry import check_expiry
from app.checks.tone_rules import check_tone_rules
from app.checks.readability import check_readability, check_sunscreen_reapply
from app.pipeline.segment import segment_text
from app.pipeline.retrieve import Retriever
from app.pipeline.redact import redact_text
from app.pipeline.llm_verify import llm_verify_finding

logger = logging.getLogger(__name__)


def _deduplicate_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate findings that flag the same text span with the same verdict."""
    seen = set()
    unique = []
    for f in findings:
        key = (
            f.get("span_start", 0),
            f.get("span_end", 0),
            f.get("flagged_text", ""),
            f.get("verdict", ""),
            f.get("category", ""),
        )
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


async def review(
    text: str,
    rules: List[Dict[str, Any]],
    ledger: List[Dict[str, Any]],
    terms: List[Dict[str, Any]],
) -> tuple[List[Dict[str, Any]], str]:
    """
    Run the full review pipeline on a piece of text.

    Returns: (list of findings, ai_status)
    """
    all_findings: List[Dict[str, Any]] = []
    ai_status = "available"

    # ── Step 1: Deterministic checks (no AI, always run) ─────────
    logger.info("Running deterministic checks...")

    # Terms check
    term_findings = check_terms(text, terms, rules)
    all_findings.extend(term_findings)

    # Claims check (superlatives, guarantees, medical)
    claim_findings = check_claims(text, ledger, rules)
    all_findings.extend(claim_findings)

    # Numbers check
    number_findings = check_numbers(text, ledger, rules)
    all_findings.extend(number_findings)

    # Expiry check
    expiry_findings = check_expiry(text, ledger, rules)
    all_findings.extend(expiry_findings)

    # Tone rules check
    tone_findings = check_tone_rules(text, rules)
    all_findings.extend(tone_findings)

    # Readability check
    readability_findings = check_readability(text, rules)
    all_findings.extend(readability_findings)

    # Sunscreen reapply check (R5)
    reapply_findings = check_sunscreen_reapply(text, rules)
    all_findings.extend(reapply_findings)

    logger.info(f"Deterministic checks produced {len(all_findings)} findings")

    # ── Step 2: Segment + Retrieve for LLM verification ──────────
    segments = segment_text(text)
    claim_segments = [s for s in segments if s["has_claim"]]

    if claim_segments:
        retriever = Retriever()
        retriever.index(rules, ledger)

        # Build source text map for quote verification
        source_texts = {}
        for r in rules:
            source_texts[str(r.get("id", ""))] = r["text"]
        for le in ledger:
            full_text = f"{le['claim']}. {le.get('evidence', '')}. {le.get('allowed_wording', '')}"
            source_texts[str(le.get("id", ""))] = full_text

        # ── Step 3: LLM verification (only for claims not already settled) ─
        already_flagged_spans = set()
        for f in all_findings:
            if f.get("span_start") is not None and f.get("span_end") is not None:
                already_flagged_spans.add((f["span_start"], f["span_end"]))

        for segment in claim_segments:
            # Skip if this span is already covered by a deterministic finding
            seg_covered = False
            for (s, e) in already_flagged_spans:
                if (segment["start"] <= s < segment["end"]) or (s <= segment["start"] < e):
                    seg_covered = True
                    break

            if seg_covered:
                continue

            # Redact before sending to LLM
            redacted = redact_text(segment["text"])

            # Retrieve relevant sources
            sources = retriever.retrieve(redacted, top_k=3)

            if not sources:
                continue

            # Call LLM
            try:
                finding, status = await llm_verify_finding(
                    redacted, sources, source_texts
                )
                if status == "unavailable":
                    ai_status = "unavailable"

                if finding and finding.get("verdict") != "supported":
                    # Adjust span to match original text position
                    finding["span_start"] = segment["start"]
                    finding["span_end"] = segment["end"]
                    all_findings.append(finding)
            except Exception as e:
                logger.error(f"LLM verification failed for segment: {e}")
                ai_status = "unavailable"

    # ── Step 4: Deduplicate ──────────────────────────────────────
    all_findings = _deduplicate_findings(all_findings)

    # ── Step 5: Sort by severity ─────────────────────────────────
    severity_order = {"high": 0, "medium": 1, "low": 2}
    all_findings.sort(key=lambda f: severity_order.get(f.get("severity", "low"), 3))

    logger.info(f"Total findings after dedup: {len(all_findings)}")

    return all_findings, ai_status
