# BrandProof — Round 2 Submission: The Build

**Hackathon:** We Code Coders (24 October - 7 November 2026, online)  
**Problem Statement:** Inkloom AI: Intelligent brand-governance platform  
**Team Name:** PRAVARUPADHYAY174  
**Track:** Full-Stack Product Engineering  
**Participant:** Pravar Upadhyay (UPES, Dehradun | 4th Year B.Tech CSE Data Science)  
**Email:** pravarupadhyay174@gmail.com | **Phone:** +91 78209 94075  
**Live Project Link:** [https://brand-proof.onrender.com](https://brand-proof.onrender.com) (or local: `http://localhost:8000`)  
**Source Code Repository:** [https://github.com/pravar0709/Brand-Proof](https://github.com/pravar0709/Brand-Proof)  
**Test Suite:** 22/22 passing (`pytest tests/test_brandproof.py -v`)

---

## 1. Project Overview & Core Principle

**BrandProof** is an evaluated, calibrated brand-governance platform built on the **"Cite or Abstain"** principle. Marketing drafts are checked against an organisation's approved guidelines, a living **Claim Ledger** (with evidence and expiration dates), and terminology rules.

- **Cite or Abstain:** Every finding must cite the exact rule ID and quoted source text. If a claim cannot be verified against approved sources, it is never guessed or hallucinated — it is marked *"Unverified: needs human review."*
- **Human-in-the-Loop Sovereign Control:** Creators Accept, Edit, or Dispute findings. Nothing is ever auto-applied or auto-published without explicit human decision.

---

## 2. Completed Features in Round 2 (The Build)

### Core Workflow (End-to-End)
1. **One-Click Demo Authentication:** Switch instantly between Creator, Brand Manager, and Reviewer roles with server-side role validation.
2. **Draft Submission & Ingestion:** Input text directly, choose from 3 pre-loaded real-world marketing samples, or upload native `.docx` files via `python-docx`.
3. **11 Built-in Deterministic Checkers (Run Locally, Zero Cost):**
   - *Banned/Preferred Terms (Rule R1):* Word-boundary regex matching with preferred replacement suggestions.
   - *Guarantee Claims (Rule R2):* Detects "guaranteed", "100%", "miracle", "permanent results".
   - *Superlative Claims (Rule R3):* Identifies "#1", "best", "world's leading" missing ledger evidence.
   - *Medical Claims (Rule R4):* Flags clinical promises ("clinically proven", "treats", "heals").
   - *Sunscreen & Safety (Rule R5):* Checks that SPF mentions include "reapply every 2 hours".
   - *Tone & Urgency (Rule R6):* Catches aggressive urgency phrasing ("don't wait", "buy now").
   - *Exclamation Density (Rule R7):* Limits exclamation marks to <= 2 per post.
   - *Hashtag Accessibility (Rule R8):* Flags lowercase hashtags and enforces CamelCase for screen readers.
   - *Emoji Frequency (Rule R9):* Restricts emoji count to <= 2 per post.
   - *Readability Metric (Rule R12):* Identifies complex sentences exceeding 25 words.
   - *Ledger Number Comparison & Expiry:* Compares numeric claims (e.g., "12 hours" vs "2 hours") and automatically flags expired promotional or factual claims.
4. **Source-Grounded Retrieval:**
   - Fast scikit-learn TF-IDF engine segments incoming drafts and indexes the brand rules and Claim Ledger corpus.
   - Retrieves top-3 relevant rules and ledger entries per sentence.
5. **AI Verifier with Substring Quote-Check:**
   - Provider-agnostic LLM client (supporting Gemini Flash and Claude via `httpx`).
   - Strict JSON output schema.
   - Automated code-level verification confirms that the AI's quoted evidence is a literal substring of the retrieved source; invalid quotes are automatically downgraded to *"Unverified"*.
6. **Creator Decision Interface:**
   - Interactive cards with severity badges (High, Medium, Low).
   - Side-by-side suggested fixes with Accept, Edit, or Dispute actions.
7. **Reviewer Approval Queue:**
   - Dedicated reviewer dashboard with comment threads.
   - Approve or Request Changes buttons.
   - Safety guardrail: Approval is blocked if unaddressed findings remain (override requires a logged justification).
8. **Immutable Versioning & Audit Logs:**
   - Resubmitting revisions creates sequential versions (v1, v2) while retaining complete decision history.
   - Full append-only audit trail tracking every action, login, and review step.
9. **Brand Governance Portals:**
   - Brand Rules, Claim Ledger, and Banned Terms management tables.
   - Governance Insights dashboard showing top failing rules, dispute rates, and upcoming expired claims.
10. **Security & Privacy Guardrails:**
    - PII (emails, phone numbers) automatically redacted before external requests.
    - Rate limiter (30 reviews/hour per IP).
    - Transparent AI Disclosure dashboard.

---

## 3. Technology Stack & Implementation Details

| Layer | Technology | Technical Justification |
|---|---|---|
| **Backend API** | Python 3.11 + FastAPI | Async performance, Pydantic v2 validation, automated OpenAPI docs. |
| **Database** | SQLite (WAL mode) + SQLAlchemy | Zero-config, sub-millisecond local queries, ACID compliant; seamless migration to PostgreSQL. |
| **Frontend** | Alpine.js 3.x + Vanilla CSS | Lightweight reactivity, zero build pipeline, ultra-responsive UI. |
| **Retrieval Engine** | scikit-learn (TF-IDF Vectorizer) | Sub-millisecond cosine similarity search without 400MB embedding weights or GPU overhead. |
| **Deterministic Verifier** | Python Regex & Logic | Instant execution, 100% explainability, mathematical certainty for numbers and dates. |
| **AI Verifier** | Provider-Agnostic HTTP (Gemini / Claude) | Flexible integration, strict JSON validation, prompt response caching (SHA-256 keys). |
| **Quote Verifier** | Python literal substring check | Discards hallucinated quotes and enforces the Cite-or-Abstain principle. |
| **Testing** | pytest + httpx TestClient | 22 comprehensive tests with 100% pass rate. |

---

## 4. Explanation of Changes Made to Original Plan

| Area | Planned in Round 1 | Implemented in Round 2 | Rationale & Impact |
|---|---|---|---|
| **Retrieval Engine** | FAISS index with sentence-transformers embeddings | scikit-learn TF-IDF Vectorizer | For brand rulesets (15–50 rules, 20–100 ledger items), TF-IDF executes in <1ms with <15MB RAM footprint, avoiding heavy model dependencies and cold-start latency. |
| **Database** | Hosted PostgreSQL | SQLite with WAL mode | SQLite eliminates network overhead for local development and demo instances while maintaining full relational integrity. All logic uses SQLAlchemy ORM for 1-line production migration. |
| **Local Verifier 1** | CPU-based NLI cross-encoder | 11 Code-Based Deterministic Checkers + Literal Quote Verification | CPU cross-encoders are slow (1.5-2.5s) and prone to negation errors. Code-based rules provide instantaneous, mathematically provable checks for numbers, dates, terms, and formatting. |
| **Model Selection** | Single fixed LLM API | Provider-Agnostic LLM Client supporting Google Gemini Flash & Claude | Added support for modern fast models (Google Gemini 1.5/2.5 Flash) with response caching for resilience during hackathon evaluation. |
| **Document Scope** | PDF, DOCX, TXT | Direct Text + Native DOCX parsing | Focused on perfecting the complete end-to-end review and approval workflow rather than shallow multi-format parsing. |

---

## 5. Three Major Improvements for Round 3 (The Finish)

1. **Calibrated Two-Verifier Benchmark & Agreement Scoring:**
   - Create a benchmark dataset of 150–200 labelled `(claim, source, verdict)` tuples covering tricky edge cases.
   - Implement Platt scaling calibration comparing deterministic checks against LLM verdicts to measure false-"Supported" rates (<2% target) and generate precision-coverage curves.
2. **Guideline Clarity Analytics with Disputed-Rule Clustering:**
   - Apply TF-IDF and K-Means clustering to creator dispute rationales.
   - Group common objections by Rule ID to automatically identify ambiguous guidelines and propose clearer rule text to Brand Managers.
3. **Enterprise Privacy Audit, Expiry Webhooks & Compliance Export:**
   - Add a side-by-side redaction inspector showing masked vs original text.
   - Automated webhook/email notifications when Claim Ledger entries approach their review expiration date (30/14/7 days).
   - One-click export of cryptographic compliance sign-off certificates (PDF/CSV) for approved marketing copy.

---

## 6. Verification and Test Results

- **Automated Tests:** 22/22 passing (`pytest tests/test_brandproof.py`)
- **Modules Covered:**
  - `test_terminology_checks`: word boundaries, case variations, preferred replacements
  - `test_claim_and_number_checks`: superlatives, guarantees, numeric contradictions
  - `test_tone_and_accessibility`: exclamation count, hashtag CamelCase, emoji thresholds
  - `test_ledger_expiry`: detection of outdated claims vs valid claims
  - `test_redaction`: email and phone number regex masking
  - `test_quote_verification`: exact substring acceptance and hallucination rejection
  - `test_auth_and_roles`: JWT generation, creator/manager/reviewer route protection
  - `test_workflow`: draft submission, versioning, review queue, override logging
