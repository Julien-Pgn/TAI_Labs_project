import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

app = FastAPI()


class AskRequest(BaseModel):
    question: str


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.post("/ask")
def ask(req: AskRequest):
    try:
        client = OpenAI()  # reads OPENAI_API_KEY from the environment
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": req.question}],
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"answer": response.choices[0].message.content}
