# TAI Labs – /ask API

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add your OpenAI key
uvicorn main:app --reload
```

Open http://localhost:8000 for the chat UI (or http://localhost:8000/docs for the API explorer).

```bash
curl -X POST localhost:8000/ask -H "Content-Type: application/json" \
  -d '{"question": "What is FastAPI?"}'
```
