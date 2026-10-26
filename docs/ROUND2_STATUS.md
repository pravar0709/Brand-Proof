# Round 2 Status – BrandProof

## Feature Status

| Feature | Status | Notes |
|---|---|---|
| **FastAPI backend with health check** | ✅ Done | `/healthz` endpoint, Dockerfile, render.yaml |
| **SQLite database with ORM models** | ✅ Done | All 9 tables: users, rules, ledger, terms, submissions, versions, findings, comments, audit_log |
| **Seed data (GlowLeaf brand)** | ✅ Done | 14 rules, 10 ledger entries (1 expired), 10 terms, 3 sample drafts |
| **Demo auth (no signup)** | ✅ Done | 3 demo users (Asha/Creator, Meera/Manager, Rohan/Reviewer), signed tokens |
| **Role-based access control** | ✅ Done | Server-side enforcement on every route |
| **Banned/preferred term detection** | ✅ Done | Word-boundary regex, cites rule + term row |
| **Superlative/guarantee/medical claim detection** | ✅ Done | Regex lexicon with Ledger lookup |
| **Number extraction + Ledger comparison** | ✅ Done | SPF, hours, %, Rs – mismatch → contradicted |
| **Expired Ledger entry detection** | ✅ Done | N-gram phrase matching against expired entries |
| **Tone rule checks** | ✅ Done | Exclamation density, ALL CAPS, fear/aggressive words |
| **Emoji count check (R9)** | ✅ Done | Max 2 emojis per post |
| **Hashtag CamelCase check (R8)** | ✅ Done | Flags all-lowercase hashtags |
| **Readability check (R12)** | ✅ Done | Average sentence length under 25 words |
| **Sunscreen reapply rule (R5)** | ✅ Done | SPF mention without "reapply" → flagged |
| **TF-IDF retrieval** | ✅ Done | scikit-learn TfidfVectorizer over rules + ledger |
| **Text segmentation** | ✅ Done | Sentence splitting with claim detection |
| **LLM verification module** | ✅ Done | Gemini + Anthropic via httpx, strict JSON, 15s timeout |
| **Quote verification** | ✅ Done | Normalised substring check, downgrades fabricated quotes |
| **Text redaction** | ✅ Done | Emails, phones, configurable terms masked |
| **LLM cache fallback** | ✅ Done | SHA256-keyed cache, sample drafts work without API key |
| **Deterministic fallback** | ✅ Done | All code-based findings work when LLM unavailable |
| **AI badge on findings** | ✅ Done | Clear visual indicator for AI-generated findings |
| **Confidence labeling** | ✅ Done | High/Medium/Low, deterministic=High, LLM capped at Medium |
| **Finding decisions (Accept/Edit/Dispute)** | ✅ Done | Persist in DB, dispute requires reason |
| **Submission workflow** | ✅ Done | Draft → In Review → Approved/Changes Requested |
| **Version history** | ✅ Done | Resubmit creates new version, old findings preserved |
| **Comments** | ✅ Done | Any role can comment on submissions |
| **Approval blocking** | ✅ Done | Blocks if pending findings, override with logged reason |
| **DOCX upload** | ✅ Done | python-docx extraction |
| **Rules CRUD** | ✅ Done | Manager can create/read/update/delete rules |
| **Rules import** | ✅ Done | Parse numbered text into rules with preview |
| **Ledger CRUD** | ✅ Done | With expiry date tracking |
| **Terms CRUD** | ✅ Done | Banned/preferred management |
| **Insights** | ✅ Done | Top flagged rules, dispute counts, expiring ledger entries |
| **Disclosure page** | ✅ Done | Code vs AI checks, services, data handling, limitations |
| **Audit log** | ✅ Done | Login, submission, review, decision, comment, approval events |
| **Rate limiting** | ✅ Done | 30 review runs/hour/IP |
| **Landing page** | ✅ Done | Role buttons, "How it works" strip, AI disclosure link |
| **Creator view** | ✅ Done | Sample loader, text area, DOCX upload, findings with highlights |
| **Manager view** | ✅ Done | Rules/Ledger/Terms tabs, expired rows in red |
| **Reviewer view** | ✅ Done | Queue, findings with decisions, comments, approve/request changes |
| **Responsive design** | ✅ Done | Works on mobile, keyboard accessible |
| **Tests (22)** | ✅ Done | All pass: terms, claims, numbers, expiry, hashtags, reapply, emoji, quote check, redact, LLM fallback, role guards, approval, disputes, versioning |
| **Dockerfile** | ✅ Done | python:3.11-slim, runs on $PORT |
| **render.yaml** | ✅ Done | Render deployment config |
| **Suggestion templates** | ✅ Done | Rule-based suggestions for all deterministic findings |
| **Apply accepted changes** | ✅ Done | Builds new draft from accepted/edited findings |
| **PDF/image processing** | ❌ Not yet | Out of scope for Round 2 |
| **NLI second verifier** | ❌ Not yet | Deferred to Round 3 (memory constraint) |
| **Guideline Clarity analytics** | ❌ Not yet | Round 3 feature |

## Changes from the Original Plan

1. **FAISS / sentence-embeddings → TF-IDF**: With only 14 rules and 10 ledger entries, TF-IDF provides excellent retrieval quality without requiring GPU, torch, or heavy dependencies. Keeps memory under 400MB.

2. **PostgreSQL → SQLite**: Zero-configuration single-file database. SQLAlchemy abstraction means the switch is a one-line change. Appropriate for demo scale.

3. **Local NLI second verifier → Deferred to Round 3**: Free-tier memory budget (400MB) doesn't support loading a transformer model. The quote-check mechanism provides a code-based alternative for verifying AI citations.

4. **PDF/image review → Out of scope**: Focus on text and DOCX to deliver a complete, working end-to-end path rather than partial file format support.

5. **Core Cite-or-Abstain pipeline → Unchanged**: The deterministic checks + quote verification approach is exactly as planned. Code-based findings cite rules/ledger entries; AI findings are quote-checked; unverifiable findings are honestly labeled.

## Round 3 Improvements (Planned)

1. **Calibrated two-verifier agreement**: A labelled ~150-pair benchmark of (claim, source, expected_verdict) tuples. Compare deterministic checker, LLM verifier, and combined agreement. Measure baselines and false-"Supported" rate. Use disagreement as an additional signal for confidence calibration.

2. **Guideline Clarity analytics**: Cluster disputed findings by rule code. Identify rules that generate the most disputes (likely poorly worded or ambiguous). Surface these to managers with recommendations to clarify the rule text.

3. **Privacy mode with enhanced disclosure**: Per-finding redaction visibility (show what was masked before LLM), browsable audit log in the UI, Ledger-expiry alerts dashboard, and exportable compliance reports.
