# TAI Labs — Project Log

Living document shared across all coding sessions. **Read this first at the start of a session and update it at the end** (status, decisions, log entry).

## Goal
Bootcamp **Week 1 assignment: "Ship your first AI endpoint"**. A typed FastAPI `/ask` endpoint in front of OpenAI that returns a structured answer with `tokens_used` and `cost_usd`. It is deployed on Render (public HTTPS URL) and has a Streamlit UI. Keep it simple.

## Constraints
- **Budget: 10 € total for the whole project** (OpenAI usage). Prefer the cheapest models and short answers, and avoid unnecessary live API calls when testing.
- Never commit secrets: the OpenAI key lives only in `.env` (git-ignored) and in Render's environment variables. Never print `.env` or paste the key in chat.
- **The GitHub repo `Julien-Pgn/TAI_Labs_project` is PUBLIC.** Never write the live Render URL in any committed file (README, this file, code). It is submitted privately in Maven only, because anyone with the link can spend the credits.
- CLAUDE.md asks Claude to briefly explain what it does, to teach AI engineering.

## Assignment checklist
| # | Requirement | Status | Who / proof |
|---|---|---|---|
| 1 | Starter repo, run locally with key in `.env`, `.env` gitignored | ✅ Code runs locally. `.env` is ignored and has never been committed (`git check-ignore -v .env`). No starter repo link was found, so we built our own that matches the class API format (see Decisions) | Proof: screenshot of `git check-ignore -v .env` + `git status` |
| 2 | Deploy to Render with `OPENAI_API_KEY` as an env var, public HTTPS URL | ⏳ `render.yaml` ready; not deployed yet | **User**: push, then Render → New → Blueprint, paste the key |
| 3 | Live `/ask` returns JSON with `answer`, `tokens_used`, `cost_usd` | ✅ Implemented and tested locally; ⏳ live proof needs OpenAI credits | **User**: curl the Render URL and screenshot it (headline proof) |
| 4 | Streamlit UI that calls `/ask` + screenshot | ✅ `streamlit_app.py` built and tested with a fake API | **User**: screenshot after the live deploy |
| 5 | Submit the live URL privately in Maven | ⏳ | **User** |
| 6 | Wallet safety: auto-recharge OFF, $5–10 budget with alert, key never in chat or committed | ✅ Code-side limits done; ⏳ OpenAI dashboard settings | **User**: buy $5 of credits, turn auto-recharge off, set budget + alert, screenshot |
| + | Optional: `force_bad` guardrail demo | ✅ Implemented and tested | Screenshot of the curl or Streamlit output with `attempts` |
| + | Optional: justify model choice and per-call cost | ✅ In README (estimates; update with measured numbers after first live calls) | — |
| + | Optional: polish README | ✅ | — |
| + | Optional: LinkedIn post (screenshots only; crop out any URL) | ⏳ | **User** |

## Current status
- API rebuilt to the class format: `POST /ask` (structured answer + guardrail + retry + `force_bad` + tokens/cost/latency), `GET /health`, `GET /docs`, chat page at `GET /`.
- Streamlit UI (`streamlit_app.py`), tests (`test_main.py`, 10 passing, OpenAI faked) and Render blueprint (`render.yaml`) are ready.
- **User added OpenAI credits.** The first real call succeeded locally: gpt-4.1-nano, 150 tokens, $0.0000285, 2.4 s, guardrail passed on attempt 1.
- User set up Render, but the service can't get the new code until the push works (see Session log: SSH passphrase).
- Local `.env` now uses `OPENAI_MODEL=gpt-4.1-nano`.
- The 2026-09-30 work is committed locally but **not pushed yet**: SSH push fails until the user unlocks their key once.

## Stack
- **Python 3.12** (`.python-version`; managed by `uv`, same version on Render). The venv in `.venv/` was created with `uv venv --seed`.
- FastAPI 0.142, uvicorn 0.54, openai SDK **3.22**, python-dotenv, Pydantic 2 (pinned in `requirements.txt`)
- Streamlit 1.64, requests, pytest (in `requirements-dev.txt`, local only)
- Git: branch `main`, remote `git@github.com:Julien-Pgn/TAI_Labs_project.git` (public)

## Files
| File | Purpose |
|---|---|
| `main.py` | FastAPI app: `/ask`, `/health`, `/` (chat page), guardrail, cost tracking, wallet limits |
| `streamlit_app.py` | Streamlit UI calling `/ask` (masked API URL field, metrics, guardrail attempts, raw JSON, curl) |
| `.streamlit/config.toml` | Streamlit theme (same palette as the chat page), headless, **bound to localhost** |
| `static/index.html` | Chat UI: a single file with inline CSS/JS and no build step |
| `test_main.py` | pytest suite. `call_model` is faked; an autouse fixture forbids real OpenAI calls |
| `render.yaml` | Render Blueprint: free web service `tai-labs-ask`, Frankfurt, health check `/health`, `OPENAI_API_KEY` as a secret (`sync: false`) |
| `.python-version` | `3.12` (read by uv and Render) |
| `requirements.txt` | Server dependencies, pinned (what Render installs) |
| `requirements-dev.txt` | `-r requirements.txt` + streamlit, requests, pytest |
| `.env` | Real secrets (`OPENAI_API_KEY`, `OPENAI_MODEL`). Git-ignored |
| `.env.example` | Template of `.env` (+ optional `DAILY_REQUEST_LIMIT`). Safe to commit |
| `.gitignore` | `.env`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.streamlit/secrets.toml`, `.DS_Store` |
| `README.md` | Public project README (API, run, tests, guardrail, model choice, wallet safety, deploy). No live URL |
| `PROJECT.md` | This file: project memory across sessions |
| `CLAUDE.md` | Loads this file each session, plus working rules |

## API
- `POST /ask`
  - Request: `{"question": str (1–2000 chars, trimmed), "model": "gpt-4.1-nano"|"gpt-4o-mini"|"gpt-4.1-mini"|null, "force_bad": bool=false}`. An invalid request returns `422` before any cost.
  - Response: `{"answer": {"answer", "confidence" (0–1), "sources_needed"}, "tokens_used", "model", "latency_ms", "cost_usd", "attempts": [{"attempt", "valid", "error"}]}`
  - Errors: OpenAI failure → `502 "OpenAI error: ..."`; output invalid twice → `502 {"message", "attempts"}`; daily limit → `429`.
- `GET /health` → `{"status": "ok", "default_model", "openai_key_set"}` (never calls OpenAI, never shows the key).
- `GET /` chat page, `GET /docs` Swagger UI.

## How to run
```bash
source .venv/bin/activate                      # venv already set up (Python 3.12)
uvicorn main:app --reload                      # http://localhost:8000 (chat), /docs, /health
streamlit run streamlit_app.py                 # http://localhost:8501 (second terminal)
pytest                                         # free: OpenAI is faked
```
Fresh setup: `uv venv && uv pip install -r requirements-dev.txt && cp .env.example .env`.

## Decisions
- **No starter repo available.** The user didn't have the link; GitHub code search found none (only a classmate's copied folder, `RashWadhwa/AI-Internship`, which is not a fork). We built our own API and copied the **class API format** from three classmates' public `/openapi.json` files, which were identical: `AskRequest{question, force_bad, model}`, `Answer{answer, confidence, sources_needed}`, `AskResponse{answer, tokens_used, model, latency_ms, cost_usd}`. We added `attempts`. Classmates' `/ask` endpoints were never called (that would spend their credits).
- **Structured output + Pydantic guardrail:** OpenAI `response_format` json_schema (strict) with a hand-written schema that has no min/max keywords, so strict mode accepts it. Pydantic `Answer` then enforces the rules the schema can't: non-empty answer, confidence 0–1, a real bool. One retry; 502 if both attempts fail.
- **`force_bad` injects a known-bad output locally** (`BAD_OUTPUT`) instead of asking the model for malformed JSON (as the class version does). This is deterministic, triggers all three rules and costs no extra tokens.
- **Default model `gpt-4.1-nano`** ($0.10 / $0.40 per 1M): the cheapest non-reasoning model with strict structured output. `gpt-5-nano` ($0.05 input) was rejected because its reasoning tokens make output cost unpredictable. The newer `gpt-6-luna` ($0.10/$0.50) is untested here. Prices are from the official page, checked 2026-09-30.
- **Wallet limits in code:** model allowlist (a `Literal` type, rejected with 422), question ≤ 2000 chars, `max_completion_tokens=300`, at most 2 calls per request, `DAILY_REQUEST_LIMIT` (default 200, in memory, resets on restart), OpenAI client `timeout=30, max_retries=1`. Worst case per request ≈ $0.0004 (nano) or $0.0015 (4.1-mini); daily worst case with 200 requests ≈ $0.30.
- `render.yaml` holds the service name in a public repo, so the URL is guessable. This was accepted because of the limits above (defense in depth), and the name can be changed in the dashboard.
- **Render:** Blueprint, free plan, Frankfurt (user is in Europe), `healthCheckPath: /health`, Python from `.python-version`. The free plan sleeps after 15 minutes idle, so the first request takes about 1 minute.
- **Streamlit runs locally** (bound to `localhost`: before this, it was reachable from the network at 138.195.x.x) and is pointed at the Render URL from its sidebar. Deploying it on Render is optional (start command `streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0`, build `pip install -r requirements-dev.txt`).
- Tests live at the repo root (`test_main.py`) so plain `pytest` can import `main` without extra config.
- Simple sync endpoints (`def`); FastAPI runs them in a threadpool. The daily counter uses a lock.

## UI design (`static/index.html`)
- Structure is inspired by Claude.ai: a quiet header, a time-based greeting with suggestion cards when the chat is empty, a centered 720px chat column, user messages in bubbles on the right, answers as plain text on the left with an avatar, and a rounded message box at the bottom.
- Visual identity is original: warm oat background with a honey glow, **juniper green** accent (`#2F5D50`), **honey** (`#E8B04B`), a four-petal "bloom" logo in inline SVG that spins while thinking, **Fraunces** (headings) and **Figtree** (body) from Google Fonts, and automatic dark mode.
- Behaviour: Enter sends and Shift+Enter adds a new line; the text box grows as you type; suggestion cards only *fill* the box (no API call until you send, which protects the budget); a Copy button plus a meta line (model · tokens · cost · seconds) under each answer; friendly error messages (out of credits, bad key, unknown model, daily limit, server down); a small safe Markdown renderer that escapes HTML; animations are disabled when the system asks for reduced motion.
- Each question is sent on its own (`/ask` has no conversation memory). The UI says so in the hint line.
- All colors are CSS variables in `:root`. The Streamlit theme reuses the same palette.

## Open items / next steps
- [x] **User:** add OpenAI credits. Still to confirm: auto-recharge OFF, a budget ($5–10) with an email alert, and a screenshot of the settings.
- [x] Commit the 2026-09-30 work.
- [ ] **User:** run `ssh-add --apple-use-keychain ~/.ssh/id_ed25519` once (types the passphrase), then push.
- [ ] Check how the Render service was created (Blueprint or manual Web Service) and that it redeploys the pushed commit.
- [ ] **User:** Render → New → Blueprint → this repo → paste `OPENAI_API_KEY` → deploy. Check `/health`.
- [ ] Live proof: `curl` the Render `/ask` and screenshot it; take the Streamlit screenshot; do the `force_bad` demo.
- [x] README now shows the measured cost per call for gpt-4.1-nano.
- [ ] Submit the URL privately in Maven. Optional LinkedIn post (crop out URLs).
- [ ] Optional: conversation memory (send prior messages), which would increase token costs.

## Concepts covered so far (teaching notes)
- **Route**: a path plus a function (`/`, `/ask`, `/health`, `/docs`). **GET** reads; **POST** sends data.
- **Structured output**: asking the model for JSON in a fixed schema instead of free text.
- **Guardrail**: validating model output before trusting it (Pydantic), with a retry and a clean failure.
- **Fault injection** (`force_bad`): deliberately feeding bad data to prove the safety net works.
- **Mocking**: replacing the real OpenAI call with a fake in tests, so they are fast, repeatable and free.
- **Observability**: logging tokens, cost and latency for every call (visible in Render's Logs tab).
- **Defense in depth** for cost: prepaid cap, budget alert, model allowlist, token caps, daily limit.
- **Dev/prod parity**: the same Python and pinned package versions locally and on Render.
- **Cold start**: free Render services sleep when idle, so the first request is slow.

## Session log
### 2026-09-23 — Session 1
- Created `main.py` with `POST /ask`, plus `.env`, `.env.example`, `.gitignore`, `requirements.txt`, `README.md`.
- Tested without a key: 502 with a clear "missing credentials" message, and 422 on a missing `question`.
- User added an OpenAI key. The live test returned `429 insufficient_quota` (no credits). The key itself was accepted.
- Discussed model choice and cost control (see Decisions).
- Browser showed `ERR_CONNECTION_REFUSED` because the server had never been started. Created `.venv`, installed dependencies, started uvicorn, and verified `/docs` returns 200.
- Confirmed `.env` is not shown by `git status` (ignored correctly).
- Created `PROJECT.md` and `CLAUDE.md`.
- Built the chat UI (`static/index.html`) and served it at `GET /` from `main.py`. Verified that `/` returns 200, the JS parses, and the Markdown renderer output is correct and escapes HTML. No live OpenAI call was made (no credits yet).

### Between sessions (by the user)
- User committed and pushed (`1b6787c`, "Project creation and fastAPI endpoint functionnal") to the public GitHub repo, and added the teaching rule to `CLAUDE.md` (uncommitted).

### 2026-09-30 — Session 2 (Week 1 assignment)
- User shared the assignment. The starter repo link was unknown; searched GitHub and read three classmates' public `/openapi.json` files (identical format) and a classmate's week-1 README to learn the expected behaviour (`force_bad` = validate-then-retry demo).
- Confirmed `.env` is ignored and has never been in git history. Found that the repo is **public**, so the live URL must stay out of it.
- Checked official OpenAI prices (developers.openai.com/api/docs/pricing) and Render's Python version docs (`.python-version` accepts `3.12`).
- Installed Python 3.12.14 with uv and rebuilt `.venv` (it was 3.9.6). openai SDK is now 3.22; verified that `chat.completions.create` still takes `response_format` and `max_completion_tokens`.
- Rewrote `main.py` (class format, guardrail, `force_bad`, cost, latency, `/health`, wallet limits). Added `test_main.py` (10 tests pass), `streamlit_app.py` + `.streamlit/config.toml`, `render.yaml`, `.python-version`, `requirements-dev.txt`; pinned `requirements.txt`; updated `.gitignore`, `.env.example`, and `.env`'s model line (without displaying the file).
- Verified live locally: `/health`, `/`, `/docs` return 200; the schema matches the class format; an expensive model gets 422; `force_bad` reaches the retry, which gets OpenAI's 429 (no credits, so no cost).
- Tested the Streamlit page with `streamlit.testing` and a fake API (answer, metrics, guardrail, curl escaping, error and unreachable states). Found Streamlit exposed on the network IP and bound it to localhost.
- Updated the chat page for the new response shape (meta line, 429 message). Rewrote the README.
- Checked the pending commit: 14 files, no secret, no live URL. **The user chose not to commit yet** (they want to review first). Next: user reviews → commit + push → credits → Render.

### 2026-09-30 — Session 3
- User added OpenAI credits and set up something on Render, but `git push` failed.
- Diagnosis: the files were **staged but never committed**, and SSH failed with `Permission denied (publickey)`. The key `~/.ssh/id_ed25519` is registered on GitHub (as "M5") but has a passphrase, the SSH agent was empty after a restart, and the passphrase was not in the macOS Keychain. Git over SSH can't prompt from VS Code's push button.
- Fix: added a `Host github.com` block to `~/.ssh/config` (`IdentityFile ~/.ssh/id_ed25519`, `AddKeysToAgent yes`, `UseKeychain yes`; backup in `~/.ssh/config.bak`). The user must run `ssh-add --apple-use-keychain ~/.ssh/id_ed25519` once and type the passphrase; after that, the Keychain remembers it. Fallback if the passphrase is forgotten: switch to HTTPS with `gh auth setup-git` + an HTTPS remote.
- First real OpenAI call (local, in-process): 200, valid structured answer, 150 tokens, $0.0000285. README updated with this measured cost.
- Committed all of today's work locally (see git log).

