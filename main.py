"""TAI Labs: a typed /ask endpoint in front of OpenAI.

Flow of one request:
  1. FastAPI validates the request (question length, allowed model).
  2. The model is asked for JSON that follows the Answer schema.
  3. Guardrail: Pydantic checks that JSON. If it fails, we retry once.
  4. We return the answer with tokens used, cost and latency.
"""
import logging
import os
import threading
import time
from datetime import date
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError

load_dotenv()
log = logging.getLogger("uvicorn.error")

# Only these models can be requested, so nobody can make the API use an expensive one.
# USD per 1M tokens (input, output), from https://developers.openai.com/api/docs/pricing (2026-09-30).
PRICES = {
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1-mini": (0.40, 1.60),
}
ModelName = Literal["gpt-4.1-nano", "gpt-4o-mini", "gpt-4.1-mini"]

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-nano")
if DEFAULT_MODEL not in PRICES:
    raise RuntimeError(f"OPENAI_MODEL={DEFAULT_MODEL!r} is not allowed. Use one of: {', '.join(PRICES)}")

MAX_OUTPUT_TOKENS = 300  # caps the cost of every answer
MAX_ATTEMPTS = 2  # first try + one retry if the guardrail rejects the output
DAILY_REQUEST_LIMIT = int(os.getenv("DAILY_REQUEST_LIMIT", "200"))

SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer clearly in at most 120 words. "
    "Set confidence between 0 and 1 for how sure you are, and sources_needed to true "
    "if the answer relies on facts the reader should verify."
)

# The shape we ask OpenAI to produce ("structured output").
ANSWER_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "answer",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
                "confidence": {"type": "number"},
                "sources_needed": {"type": "boolean"},
            },
            "required": ["answer", "confidence", "sources_needed"],
            "additionalProperties": False,
        },
    },
}

# What a misbehaving model could send back. force_bad uses it to show the guardrail at work.
BAD_OUTPUT = '{"answer": "", "confidence": 1.7, "sources_needed": "maybe"}'


class AskRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=2000, examples=["What is RAG in one sentence?"])
    model: ModelName | None = Field(None, description="Defaults to OPENAI_MODEL")
    force_bad: bool = Field(False, description="Demo: replace the first answer with a bad one")


class Answer(BaseModel):
    """The guardrail: model output is only accepted if it fits these rules."""

    answer: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    sources_needed: bool


class Attempt(BaseModel):
    attempt: int
    valid: bool
    error: str | None = None


class AskResponse(BaseModel):
    answer: Answer
    tokens_used: int
    model: str
    latency_ms: int
    cost_usd: float
    attempts: list[Attempt]


app = FastAPI(title="TAI Labs /ask API")

_today = {"day": date.today(), "count": 0}
_today_lock = threading.Lock()


def count_request():
    """Refuse requests beyond the daily limit, so a leaked URL can't drain the credits."""
    with _today_lock:
        if _today["day"] != date.today():
            _today.update(day=date.today(), count=0)
        if _today["count"] >= DAILY_REQUEST_LIMIT:
            raise HTTPException(status_code=429, detail="Daily request limit reached. Try again tomorrow.")
        _today["count"] += 1


def call_model(model: str, question: str):
    """One OpenAI call. Returns the raw text the model produced and its token usage."""
    client = OpenAI(timeout=30, max_retries=1)  # reads OPENAI_API_KEY from the environment
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        response_format=ANSWER_FORMAT,
        max_completion_tokens=MAX_OUTPUT_TOKENS,
    )
    return response.choices[0].message.content or "", response.usage


def cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    price_in, price_out = PRICES[model]
    return (prompt_tokens * price_in + completion_tokens * price_out) / 1_000_000


def describe(error: ValidationError) -> str:
    return "; ".join(f"{'.'.join(map(str, e['loc'])) or 'output'}: {e['msg']}" for e in error.errors())


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health")
def health():
    """Checks the server is up without calling OpenAI (costs nothing)."""
    return {
        "status": "ok",
        "default_model": DEFAULT_MODEL,
        "openai_key_set": bool(os.getenv("OPENAI_API_KEY")),
    }


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    count_request()
    model = req.model or DEFAULT_MODEL
    start = time.perf_counter()
    attempts, tokens, cost = [], 0, 0.0

    for n in range(1, MAX_ATTEMPTS + 1):
        if req.force_bad and n == 1:
            raw = BAD_OUTPUT  # demo only: pretend the model misbehaved (no API call, no cost)
        else:
            try:
                raw, usage = call_model(model, req.question)
            except Exception as e:  # bad key, no credits, network...
                raise HTTPException(status_code=502, detail=f"OpenAI error: {e}")
            tokens += usage.total_tokens
            cost += cost_usd(model, usage.prompt_tokens, usage.completion_tokens)

        # Never trust model output until it passes the schema.
        try:
            answer = Answer.model_validate_json(raw)
        except ValidationError as e:
            attempts.append(Attempt(attempt=n, valid=False, error=describe(e)))
            continue

        attempts.append(Attempt(attempt=n, valid=True))
        latency_ms = round((time.perf_counter() - start) * 1000)
        log.info("ask model=%s tokens=%d cost=$%.6f latency=%dms attempts=%d", model, tokens, cost, latency_ms, n)
        return AskResponse(
            answer=answer,
            tokens_used=tokens,
            model=model,
            latency_ms=latency_ms,
            cost_usd=round(cost, 8),
            attempts=attempts,
        )

    raise HTTPException(
        status_code=502,
        detail={"message": "The model's answer failed validation twice.", "attempts": [a.model_dump() for a in attempts]},
    )
