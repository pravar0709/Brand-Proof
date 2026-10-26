# BrandProof — Round 2 Submission

## Project Overview

**BrandProof** is an AI-powered brand-governance review tool built on the "Cite or Abstain" principle. Content creators submit marketing drafts, and BrandProof checks every claim against the brand's approved rules, claim ledger, and term list. Every finding is backed by a specific source citation — or honestly flagged as "Unverified: needs human review."

**Core Principle:** If no supporting source exists, or the AI's quoted evidence isn't literally present in the source text, the finding is marked "Unverified." BrandProof never guesses.

---

## Completed Features

### Core Workflow (End-to-End)
- ✅ One-click demo login (Creator / Manager / Reviewer) — no signup required
- ✅ Submit marketing drafts via text input or DOCX file upload
- ✅ Automated review pipeline: 6 deterministic checks + optional AI verification
- ✅ 9+ findings generated per sample draft with severity badges, citations, and suggestions
- ✅ Creator can Accept, Edit, or Dispute each finding with reasons
- ✅ Reviewer sees submission queue, reviews findings, and Approves or Requests Changes
- ✅ Approval blocks if findings are still pending (override requires logged reason)
- ✅ Version history: resubmit creates new version, old findings preserved

### Deterministic Checks (Always Run, No AI)
- ✅ Banned/preferred term detection (word-boundary regex matching)
- ✅ Superlative, guarantee, and medical claim detection with Ledger lookup
- ✅ Number extraction and Ledger comparison (e.g., "12 hours" vs Ledger's "2 hours")
- ✅ Expired Ledger entry detection (flags outdated claims)
- ✅ Tone analysis (exclamation density, ALL CAPS, fear/aggressive language)
- ✅ Emoji count check (max 2 per post, Rule R9)
- ✅ Hashtag CamelCase accessibility check (Rule R8)
- ✅ Readability check (sentence length, Rule R12)
- ✅ Sunscreen reapply rule (SPF without "reapply every 2 hours", Rule R5)

### AI Pipeline
- ✅ TF-IDF retrieval (scikit-learn) finds top-3 relevant rules/ledger entries
- ✅ Text segmentation with claim detection
- ✅ Provider-agnostic LLM module (Gemini / Anthropic via httpx)
- ✅ Text redaction (emails, phones, confidential terms masked before LLM)
- ✅ Quote verification: AI's cited evidence checked as literal substring of source
- ✅ Graceful LLM fallback: deterministic findings always work, banner shown if AI unavailable
- ✅ LLM response cache with SHA256 keys

### Brand Management (Manager Role)
- ✅ View and manage brand rules (14 rules with codes, categories, severities)
- ✅ View claim ledger (10 entries with evidence, expiry dates, status)
- ✅ View banned/preferred terms (10 terms)
- ✅ Insights dashboard: top flagged rules, dispute counts, expiring ledger entries

### Compliance & Transparency
- ✅ AI Disclosure page: code vs AI checks, data handling, human-in-the-loop policy
- ✅ AI badge on every AI-generated finding
- ✅ Confidence labeling (High/Medium/Low — deterministic = High, AI capped at Medium)
- ✅ Full audit log for every action

### Infrastructure
- ✅ 22 passing pytest tests covering all checks, pipeline, auth, and workflow
- ✅ Dockerfile and render.yaml for one-click deployment
- ✅ Role-based access control (server-side enforcement)
- ✅ Rate limiting (30 review runs/hour/IP)
- ✅ Premium dark-themed responsive UI (Alpine.js + vanilla CSS)

---

## Technology Stack

| Layer | Technology | Why |
|---|---|---|
| Backend | Python 3.11 + FastAPI | Async support, automatic OpenAPI docs, Pydantic validation |
| Database | SQLite + SQLAlchemy ORM | Zero-config, WAL mode for concurrent reads, portable |
| Retrieval | scikit-learn TF-IDF | Lightweight, no GPU needed, excellent for 14 rules + 10 ledger entries |
| LLM | httpx → Gemini / Anthropic | Provider-agnostic, no heavy SDKs, strict JSON response format |
| Auth | itsdangerous signed tokens | Simple demo auth, no JWT complexity needed |
| Frontend | Alpine.js + vanilla CSS | No build step, reactive SPA, served as static files |
| File parsing | python-docx | DOCX text extraction |
| Testing | pytest | 22 unit + integration tests |
| Deployment | Docker + Render | One-click deploy with render.yaml |

---

## Changes from Round 1 Plan

| Original Plan | What Changed | Why |
|---|---|---|
| FAISS / sentence embeddings for retrieval | TF-IDF (scikit-learn) | With only 14 rules and 10 ledger entries, TF-IDF gives excellent results without GPU, torch, or 2GB+ dependencies |
| PostgreSQL | SQLite | Zero-config, portable, appropriate for demo scale. SQLAlchemy abstraction means switching is a one-line change |
| Local NLI second verifier | Deferred to Round 3 | Free-tier memory (400MB) doesn't support transformer models. Quote-check provides a code-based alternative |
| PDF/image review | Out of scope | Focus on complete text/DOCX workflow rather than partial format support |

**What didn't change:** The core Cite-or-Abstain pipeline is exactly as proposed. Deterministic checks cite rules/ledger; AI findings are quote-verified; unverifiable findings are honestly labeled.

---

## Three Round 3 Improvements

### 1. Calibrated Two-Verifier Agreement (Technical Depth)
Build a labelled benchmark of ~150 (claim, source, expected_verdict) tuples. Compare deterministic checker, LLM verifier, and combined agreement. Measure baselines and false-"Supported" rate. Use disagreement as an additional signal for confidence calibration. This moves from heuristic confidence to data-driven, measurable accuracy.

### 2. Guideline Clarity Analytics (Product Value)
Cluster disputed findings by rule code to identify which brand guidelines generate the most disputes (likely poorly worded or ambiguous). Surface these to managers with recommendations to clarify the rule text. This creates a feedback loop: the system gets smarter from usage data and helps organisations improve their own brand guidelines.

### 3. Privacy-First Enhanced Disclosure & Compliance Reports (Enterprise Readiness)
Add per-finding redaction visibility (show what was masked before LLM), browsable audit log in the UI, Ledger-expiry alert dashboard with notifications, and exportable compliance reports (PDF/CSV). This addresses enterprise trust and regulatory requirements, making BrandProof ready for real-world deployment in regulated industries.

---

## AI Disclosure

- **AI coding assistance**: Antigravity / Gemini and Claude used for planning and code generation
- **LLM in product**: Optional (Gemini/Anthropic) for supplementary claim verification only
- **All AI findings**: Clearly marked with 🤖 AI badge
- **Data handling**: Only redacted text sent to LLM; emails, phones, terms are masked
- **Human-in-the-loop**: No changes are auto-applied; every finding requires human decision
- **Seed data**: All data (GlowLeaf brand) is fictional/synthetic
