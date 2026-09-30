# TAI Labs · Ask API

A typed FastAPI endpoint in front of OpenAI. Send a question to `POST /ask` and get back a **structured answer** plus what it cost: tokens, USD and latency. A **guardrail** checks every model output before it reaches you.

Built for Week 1 of the AI Engineering bootcamp ("Ship your first AI endpoint").

```text
question ──▶ FastAPI validates the request (length, allowed model, daily limit)
         ──▶ OpenAI returns JSON (structured output)
         ──▶ guardrail: Pydantic checks the JSON ── fails? retry once
         ──▶ { answer, tokens_used, model, latency_ms, cost_usd, attempts }
```

## The API

| Route | What it does | Costs tokens? |
|---|---|---|
| `POST /ask` | Answers a question | Yes |
| `GET /health` | Confirms the server is up and the key is set (never shows the key) | No |
| `GET /docs` | Interactive API explorer | No |
| `GET /` | A small chat page | Only when you ask something |

**Request**

```json
{ "question": "What is RAG in one sentence?", "model": "gpt-4.1-nano", "force_bad": false }
```

`model` is optional (default `gpt-4.1-nano`) and must be one of `gpt-4.1-nano`, `gpt-4o-mini` or `gpt-4.1-mini`. `force_bad` is a guardrail demo (see below).

**Response**

```json
{
  "answer": {
    "answer": "RAG (Retrieval-Augmented Generation) lets a model look up relevant documents and use them to write its answer.",
    "confidence": 0.93,
    "sources_needed": false
  },
  "tokens_used": 154,
  "model": "gpt-4.1-nano",
  "latency_ms": 870,
  "cost_usd": 5.5e-05,
  "attempts": [{ "attempt": 1, "valid": true, "error": null }]
}
```

(Illustrative values.)

## Run it locally

Needs Python 3.12 (pinned in `.python-version`) and an OpenAI API key.

```bash
uv venv && source .venv/bin/activate      # or: python3.12 -m venv .venv && source .venv/bin/activate
uv pip install -r requirements-dev.txt    # or: pip install -r requirements-dev.txt
cp .env.example .env                      # then put your key in .env
uvicorn main:app --reload                 # API on http://localhost:8000
```

Try it:

```bash
curl -s -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is RAG in one sentence?"}'
```

### Streamlit UI

In a second terminal:

```bash
source .venv/bin/activate
streamlit run streamlit_app.py            # http://localhost:8501
```

Enter the API URL in the sidebar (your local server or your Render URL). The field is masked, so screenshots don't reveal it. The page shows the answer, tokens, cost, latency, confidence, the guardrail attempts, the raw JSON and the equivalent `curl` command.

### Tests

```bash
pytest
```

The tests replace OpenAI with a fake, so they run in under a second and cost nothing. A safety fixture makes any test fail if it tries to reach the real API.

## The guardrail and `force_bad`

LLM output is untrusted input. The model is asked for JSON in a fixed shape (OpenAI structured output), and then **Pydantic validates it anyway**. It checks rules the model can't be forced to follow: a non-empty answer, a confidence between 0 and 1, and a real boolean. If validation fails, the API retries once. If it fails twice, the API returns a `502` error instead of passing bad data along.

`"force_bad": true` swaps the first model output for a known-bad one:

```json
{"answer": "", "confidence": 1.7, "sources_needed": "maybe"}
```

The guardrail catches all three problems. The API then retries with a real model call, and `attempts` shows the whole story:

```json
"attempts": [
  { "attempt": 1, "valid": false, "error": "answer: String should have at least 1 character; confidence: Input should be less than or equal to 1; sources_needed: Input should be a valid boolean, unable to interpret input" },
  { "attempt": 2, "valid": true, "error": null }
]
```

The bad output is injected locally, so the demo always triggers and costs no extra tokens.

## Model choice and cost per call

Prices from [OpenAI's pricing page](https://developers.openai.com/api/docs/pricing), checked 2026-09-30, in USD per 1M tokens:

| Model | Input | Output | Est. cost per question* |
|---|---|---|---|
| **gpt-4.1-nano** (default) | $0.10 | $0.40 | ≈ $0.00005 |
| gpt-4o-mini | $0.15 | $0.60 | ≈ $0.00008 |
| gpt-4.1-mini | $0.40 | $1.60 | ≈ $0.0002 |

\*Measured on gpt-4.1-nano: a one-sentence answer used 150 tokens and cost $0.0000285. The other rows scale by price. Every response reports its real `cost_usd`.

**Why gpt-4.1-nano:** it's the cheapest model that doesn't reason before answering and that supports strict structured output. Short factual answers don't need a bigger model. `gpt-5-nano` has a lower input price, but it's a reasoning model: its hidden "thinking" tokens are billed as output, which makes the cost per call higher and less predictable for short answers. At about $0.00003–0.00005 per question, $5 of credit covers well over 100,000 questions.

## Wallet safety

- **Prepaid credits with auto-recharge off.** This is the hard cap, because OpenAI stops when the credits run out.
- **A budget alert** on the OpenAI project.
- **The key lives only in `.env` (git-ignored) and in Render's environment variables.** It is never committed and never pasted into chat.
- **Limits in the code:**
  - only three cheap models are allowed;
  - questions are capped at 2,000 characters and answers at 300 tokens;
  - at most 2 model calls per request;
  - a daily request limit (`DAILY_REQUEST_LIMIT`, default 200, counted in memory and reset when the server restarts).
- **The live URL is shared privately only.** Anyone who has it can spend the credits.

## Deploy to Render

1. Push this repo to GitHub.
2. In Render: **New → Blueprint**, then pick the repo. Render reads `render.yaml`.
3. When asked for `OPENAI_API_KEY`, paste your key there. It is stored as a secret environment variable.
4. Wait for the deploy, then check `https://<your-service>.onrender.com/health`.

The free plan sleeps after 15 minutes without traffic, so the first request after a pause takes about a minute.

## Files

| File | Purpose |
|---|---|
| `main.py` | The API: `/ask`, `/health`, guardrail, cost tracking |
| `streamlit_app.py` | Streamlit UI that calls `/ask` |
| `static/index.html` | Chat page served at `/` |
| `test_main.py` | Tests with a fake OpenAI (free to run) |
| `render.yaml` | Render deployment config |
| `requirements.txt` | What the server needs (installed by Render) |
| `requirements-dev.txt` | Adds Streamlit and pytest for local work |
| `.env.example` | Template for your local `.env` |
