# BrandProof

**Cite-or-Abstain brand governance.** Every finding is backed by your rules — or flagged for human review.

> 🔗 **Live URL**: _[placeholder – deploy to Render]_

## What It Does

Organisations keep a brand guide, a **Claim Ledger** (approved facts with evidence, allowed wording, and expiry dates), and a term list. A creator submits a draft. BrandProof checks it against all three sources, returns findings that **cite the exact guideline rule or Ledger entry** (quoted text), explain why, give a confidence label, and suggest an intent-preserving rewrite.

Creators accept, edit, or dispute each finding — **nothing is auto-applied**. A reviewer comments and approves or requests changes.

**Core principle: Cite or Abstain.** If no supporting source exists, or the AI's quoted evidence isn't literally present in the source, the finding is "Unverified: needs human review". Never guess.

## 60-Second Judge Walkthrough

1. Open the app → click **"Try as Creator"**
2. Sample draft 1 is pre-loaded → click **"Check My Content"**
3. Review the findings (6+ issues: unsupported "clinically proven", unsupported "#1", "guaranteed" claim, "12 hours" contradicts Ledger, expired free-shipping offer, hashtag casing, emoji overload)
4. **Accept** one finding, **Dispute** another (enter a reason)
5. Sign out → click **"Try as Reviewer"**
6. Open the submission from the queue → read findings and creator decisions
7. Click **"Approve"** (you'll get an override prompt if findings are still pending)
8. ✅ Done!

## Run Locally

```bash
# Clone
git clone <repo-url> && cd brandproof

# Install
pip install -r requirements.txt

# Configure (optional – works with LLM_PROVIDER=none)
cp .env.example .env
# Edit .env to set LLM_PROVIDER, LLM_API_KEY, LLM_MODEL if desired

# Run
uvicorn app.main:app --port 8000

# Open http://localhost:8000
```

## Run Tests

```bash
pytest tests/ -v
```

All 22 tests pass.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `LLM_PROVIDER` | No | `none` | `gemini`, `anthropic`, or `none` |
| `LLM_API_KEY` | No | — | API key for the chosen provider |
| `LLM_MODEL` | No | — | Model name (e.g. `gemini-2.0-flash`) |
| `SECRET_KEY` | No | dev default | Token signing secret |
| `PORT` | No | `8000` | Server port |

## Docker

```bash
docker build -t brandproof .
docker run -p 8000:8000 brandproof
```

## Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLite (SQLAlchemy), Pydantic
- **Frontend**: HTML + Alpine.js + CSS (no build step)
- **Retrieval**: scikit-learn TF-IDF
- **Parsing**: python-docx (DOCX), plain text
- **Auth**: Demo login with itsdangerous signed tokens
- **LLM**: Provider-agnostic (Gemini/Anthropic) via plain httpx, with cache fallback

## Honest Limitations

- **No PDF/image processing** — text and DOCX only
- **LLM verification is supplementary** — deterministic rule-based checks are the foundation
- **Demo auth only** — no real user management or password-based login
- **SQLite** — single-file database, not suitable for high-concurrency production
- **Review is an aid, not legal advice** — always have a human expert verify compliance
- **No NLI second-verifier** — deferred to Round 3 due to memory constraints
- **Seed data is fictional** — GlowLeaf is a synthetic brand for demonstration
