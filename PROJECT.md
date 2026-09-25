# TAI Labs — Project Log

Living document shared across all coding sessions. **Read this first at the start of a session and update it at the end** (status, decisions, log entry).

## Goal
A minimal FastAPI service that forwards a user's question to OpenAI and returns the answer. Keep it simple.

## Constraints
- **Budget: 10 € total for the whole project** (OpenAI usage). Prefer the cheapest models and short answers, and avoid unnecessary live API calls when testing.
- Never commit secrets: the OpenAI key lives only in `.env`, which is git-ignored.

## Current status
- `POST /ask` implemented and working locally (validation + error handling tested).
- Web chat UI served at `GET /` (`static/index.html`). Page loads and script checks pass; not yet tried with a live answer.
- Live OpenAI call **not yet successful**: the key is valid, but the account had no credits (`429 insufficient_quota`) on 2026-09-23.
- Model is still `gpt-4o-mini` in `.env`. Switching to a cheaper nano model has been discussed but not done.

## Stack
- Python 3.9.6 (macOS system Python), virtualenv in `.venv/`
- FastAPI, uvicorn, `openai` SDK, `python-dotenv` (see `requirements.txt`)
- Git repo initialized on branch `main` (no commits yet)

## Files
| File | Purpose |
|---|---|
| `main.py` | FastAPI app: `GET /` (UI) and `POST /ask` |
| `static/index.html` | Chat UI: a single file with inline CSS/JS and no build step |
| `.env` | Real secrets (`OPENAI_API_KEY`, `OPENAI_MODEL`). Git-ignored |
| `.env.example` | Template of `.env` with placeholders. Safe to commit |
| `.gitignore` | Ignores `.env`, `__pycache__/`, `.venv/` |
| `requirements.txt` | Dependencies |
| `README.md` | Setup and run instructions |
| `PROJECT.md` | This file: project memory across sessions |
| `CLAUDE.md` | Tells Claude Code to load this file each session |

## API
`GET /` → the chat UI (hidden from `/docs`).

`POST /ask`
- Request: `{"question": "..."}` (missing field → 422)
- Response: `{"answer": "..."}`
- On any OpenAI failure → `502` with the OpenAI error message in `detail`
- Model comes from `OPENAI_MODEL` (default `gpt-4o-mini`). The OpenAI client is created per request, so a missing key returns a 502 error instead of crashing the app at startup.
- It is a POST endpoint, so opening `/ask` in the browser's address bar gives `405 Method Not Allowed`. Use `http://localhost:8000/docs` to try it.

## How to run
```bash
python3 -m venv .venv && source .venv/bin/activate   # first time only
pip install -r requirements.txt                      # first time only
uvicorn main:app --reload
# → http://localhost:8000      (chat UI)
# → http://localhost:8000/docs (API explorer)
```

## Decisions
- **Simple sync endpoint** (`def`, not `async def`): FastAPI runs it in a threadpool, which is enough here.
- **Model configurable via `.env`** so the model can change without code edits (useful for cost control).
- **Cost control:** use prepaid OpenAI credits with auto-recharge **off**, which is the real hard cap on spending. A project budget alert and an output-token cap (`max_tokens`, ~300) were suggested but are not implemented yet.

## UI design (`static/index.html`)
- Structure is inspired by Claude.ai: a quiet header, a time-based greeting with suggestion cards when the chat is empty, a centered 720px chat column, user messages in bubbles on the right, answers as plain text on the left with an avatar, and a rounded message box at the bottom.
- Visual identity is original: warm oat background with a honey glow, **juniper green** accent (`#2F5D50`), **honey** (`#E8B04B`), a four-petal "bloom" logo in inline SVG that spins while thinking, **Fraunces** (headings) and **Figtree** (body) from Google Fonts, and automatic dark mode.
- Behaviour: Enter sends and Shift+Enter adds a new line; the text box grows as you type; suggestion cards only *fill* the box (no API call until you send, which protects the budget); a Copy button on answers; friendly error messages (out of credits, bad key, unknown model, server down); a small safe Markdown renderer that escapes HTML; animations are disabled when the system asks for reduced motion.
- Each question is sent on its own (`/ask` has no conversation memory). The UI says so in the hint line.
- All colors are CSS variables in `:root`. Change them there to restyle the page.

## Open items / next steps
- [ ] Add OpenAI credits (≤ 10 €, auto-recharge off) and re-test `/ask` live.
- [ ] Choose the cheapest suitable model and set `OPENAI_MODEL` (check names/prices at https://developers.openai.com/api/docs/pricing). Candidates as of Sep 2026: GPT-5.4 nano, GPT-5.6 Luna (~$0.20 / 1M input tokens).
- [ ] Optionally cap answer length (`max_tokens`) in `main.py`.
- [ ] First git commit.
- [ ] Optional: conversation memory (send prior messages to `/ask`), which would increase token costs.

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
