# AI Disclosure – BrandProof

## AI Coding Assistance

This application was developed with AI coding assistance:

- **Antigravity / Gemini** — used for planning, code generation, and architecture decisions
- **Claude (Anthropic)** — used for code generation and review

All generated code was reviewed and tested by the development team.

## Libraries & Services

| Component | Library / Service | Purpose |
|---|---|---|
| Web framework | FastAPI 0.104.1 | REST API and static file serving |
| Database | SQLAlchemy 2.0.23 + SQLite | Data persistence |
| Validation | Pydantic 2.5.2 | Request/response validation |
| Auth tokens | itsdangerous 2.1.2 | Signed demo tokens |
| HTTP client | httpx 0.25.2 | LLM API calls |
| Text retrieval | scikit-learn 1.3.2 | TF-IDF vectorisation for rule/ledger retrieval |
| Text retrieval (alt) | rank-bm25 0.2.2 | BM25 ranking (available as alternative) |
| DOCX parsing | python-docx 1.1.0 | Extract text from DOCX files |
| Frontend | Alpine.js 3.x | Reactive SPA without build step |
| Testing | pytest 7.4.3 | Unit and integration tests |

## LLM Provider

- **Provider**: Configurable via `LLM_PROVIDER` env var (`gemini`, `anthropic`, or `none`)
- **Model**: Configurable via `LLM_MODEL` env var (not hardcoded)
- **Purpose**: Supplementary claim verification for tone and context that rule-based checks cannot determine
- **Data sent**: Only **redacted** text (emails, phone numbers, and confidential terms are masked before sending)
- **Fallback**: If the LLM is unavailable, all deterministic (rule-based) findings still work. A banner informs the user.

## What Is Checked by Code vs AI

### Code-based checks (always run, no external calls):
- Banned/preferred term detection (word-boundary regex)
- Superlative, guarantee, and medical claim detection
- Number extraction and Ledger comparison (e.g., "12 hours" vs "2 hours")
- Expired Ledger entry detection
- Tone analysis (exclamation marks, ALL CAPS, fear/aggressive language)
- Emoji count and hashtag CamelCase accessibility check
- Readability (average sentence length)
- Sunscreen reapply rule (R5)

### AI-assisted checks (optional, clearly marked):
- Contextual claim verification for claims not fully resolved by code
- Suggested rewrites (marked with "AI" badge)
- Quote verification: AI's cited evidence is checked against source text; if not found, the finding is downgraded to "Unverified"

## Human-in-the-Loop

- No changes are ever auto-applied
- Every finding requires a human decision: Accept, Edit, or Dispute
- A reviewer must explicitly approve submissions
- Approval is blocked if findings are still pending (unless the reviewer provides an override reason, which is logged)
- Creators can dispute any finding with a reason

## Synthetic Data

- The brand "GlowLeaf" is entirely fictional
- All rules, ledger entries, terms, and sample drafts are synthetic
- No real confidential, personal, or proprietary data is used anywhere in this application
