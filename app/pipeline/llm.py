"""Provider-agnostic LLM module with cache fallback."""

import os
import json
import hashlib
import logging
from typing import Optional, Dict, Any, List

import httpx

logger = logging.getLogger(__name__)

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "none")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "")
LLM_TIMEOUT = 15  # seconds
LLM_MAX_RETRIES = 1

# Load cache
_cache: Dict[str, Any] = {}
_cache_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "seed", "llm_cache.json"
)


def _load_cache():
    global _cache
    try:
        if os.path.exists(_cache_path):
            with open(_cache_path, "r", encoding="utf-8") as f:
                _cache = json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load LLM cache: {e}")
        _cache = {}


def _save_cache():
    try:
        with open(_cache_path, "w", encoding="utf-8") as f:
            json.dump(_cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Failed to save LLM cache: {e}")


def _cache_key(sentence: str, source_ids: List[str]) -> str:
    """Generate cache key from normalised sentence + source IDs."""
    normalised = " ".join(sentence.lower().split())
    key_material = normalised + "|" + ",".join(sorted(str(s) for s in source_ids))
    return hashlib.sha256(key_material.encode()).hexdigest()


# Load cache on module import
_load_cache()


SYSTEM_PROMPT = """You are a brand compliance reviewer. You MUST follow these rules strictly:

1. You are given a piece of text and a set of source documents (brand rules and claim ledger entries).
2. For each claim or statement in the text, determine if it is supported, contradicted, outdated, or unverified by the provided sources.
3. You MUST answer "unverified" if NO provided source supports or contradicts the claim. NEVER use outside knowledge.
4. Your evidence_quote MUST be a VERBATIM substring from the provided source text. Do not paraphrase or fabricate quotes.
5. Your suggestion must preserve the creator's original intent while fixing the issue.

Respond with ONLY valid JSON (no markdown, no explanation outside the JSON)."""


def _build_user_prompt(sentence: str, sources: List[Dict[str, Any]]) -> str:
    """Build the user prompt with redacted text and sources."""
    sources_text = ""
    for i, src in enumerate(sources):
        src_type = src.get("type", "unknown")
        src_id = src.get("id", i)
        if src_type == "rule":
            sources_text += f"\n[Source {src_id} - Rule {src.get('code', '')}]: {src.get('text', '')}"
        else:
            sources_text += f"\n[Source {src_id} - Ledger]: {src.get('claim', '')}. {src.get('text', '')}"

    return f"""Review this text against the provided sources:

TEXT: "{sentence}"

SOURCES:{sources_text}

Respond with ONLY this JSON structure:
{{
  "verdict": "supported|contradicted|outdated|unverified",
  "source_id": "<id of the most relevant source, or null if unverified>",
  "evidence_quote": "<verbatim quote from the source that supports your verdict, or empty string if unverified>",
  "explanation": "<brief explanation of why this verdict>",
  "suggestion": "<rewrite preserving the creator's intent while fixing the issue, or the original text if no issue>",
  "confidence": 0.0-1.0
}}"""


async def _call_gemini(prompt: str, system: str) -> Optional[Dict]:
    """Call the Gemini REST API."""
    if not LLM_API_KEY or not LLM_MODEL:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{LLM_MODEL}:generateContent"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system}]},
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1,
        },
    }

    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    json=payload,
                    params={"key": LLM_API_KEY},
                    timeout=LLM_TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()

                # Extract text from Gemini response
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text)
        except Exception as e:
            logger.warning(f"Gemini API attempt {attempt + 1} failed: {e}")
            if attempt == LLM_MAX_RETRIES:
                return None


async def _call_anthropic(prompt: str, system: str) -> Optional[Dict]:
    """Call the Anthropic REST API."""
    if not LLM_API_KEY or not LLM_MODEL:
        return None

    url = "https://api.anthropic.com/v1/messages"

    payload = {
        "model": LLM_MODEL,
        "max_tokens": 1024,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }

    headers = {
        "x-api-key": LLM_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=LLM_TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()
                text = data["content"][0]["text"]
                # Parse JSON from response (might be wrapped in markdown)
                text = text.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1].rsplit("```", 1)[0]
                return json.loads(text)
        except Exception as e:
            logger.warning(f"Anthropic API attempt {attempt + 1} failed: {e}")
            if attempt == LLM_MAX_RETRIES:
                return None


async def verify_claim(
    sentence: str,
    sources: List[Dict[str, Any]],
) -> tuple[Optional[Dict], str]:
    """
    Verify a claim against sources using LLM.

    Returns: (result_dict or None, status: "available"|"cached"|"unavailable")
    """
    source_ids = [str(s.get("id", "")) for s in sources]
    key = _cache_key(sentence, source_ids)

    # Check cache first
    if key in _cache:
        logger.info(f"LLM cache hit for key {key[:16]}...")
        return _cache[key], "cached"

    # Check if LLM is available
    if LLM_PROVIDER == "none" or not LLM_API_KEY:
        logger.info("LLM provider is 'none' or no API key – skipping LLM verification")
        return None, "unavailable"

    # Build prompt
    user_prompt = _build_user_prompt(sentence, sources)

    # Call the appropriate provider
    result = None
    if LLM_PROVIDER == "gemini":
        result = await _call_gemini(user_prompt, SYSTEM_PROMPT)
    elif LLM_PROVIDER == "anthropic":
        result = await _call_anthropic(user_prompt, SYSTEM_PROMPT)

    if result is None:
        return None, "unavailable"

    # Validate the result has required fields
    required_fields = ["verdict", "evidence_quote", "explanation", "suggestion", "confidence"]
    if not all(f in result for f in required_fields):
        logger.warning(f"LLM result missing required fields: {result}")
        return None, "unavailable"

    # Validate verdict value
    valid_verdicts = {"supported", "contradicted", "outdated", "unverified"}
    if result.get("verdict") not in valid_verdicts:
        result["verdict"] = "unverified"

    # Cache the result
    _cache[key] = result
    _save_cache()

    return result, "available"
