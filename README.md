# Sugar Path

Sugar Path is a local, demo-only diabetes companion prototype. It uses a
fictional patient and synthetic health data; it is not medical software and
does not provide diagnosis, emergency care, or dosing advice.

## Current scope: Phases 1–2

The current implementation provides a FastAPI + SQLite backend that seeds
Rahul Sen with 15 days of synthetic readings and daily events, plus a
mobile-first React dashboard. It now includes a deterministic five-minute Mock
CGM feed, glucose graph, medicine confirmation, natural-language meal logging
using only a local food table, activity/sleep history views, and an optional
Ollama-powered Ask Sugar Path assistant. Weekly reporting, persistent memory,
and notifications remain later phases.

## Ask Sugar Path and Ollama

Set `OLLAMA_MODEL` in `.env` to the name of a locally installed model that
supports tool calling. Start Ollama, pull that model, then start Sugar Path:

```powershell
ollama serve
ollama pull <your-tool-calling-model>
```

Sugar Path sends the configured model only the patient question, safety policy,
and explicit tool schemas. The model can request structured backend tools for
glucose, meals, medicine, activity, sleep, profile, and a daily summary.
Validated tools are the only way it can read or write application data.

If Ollama is not running, all non-chat features continue working and the chat
shows that Sugar Path's AI assistant is temporarily unavailable. Models with
reliable multi-turn function/tool-calling support are recommended; models that
only produce plain text cannot complete patient-specific tool retrieval.

Try: “Did I take my morning medicine?”, “Why did my glucose rise this
morning?”, “What did I eat before my highest glucose today?”, “How much did I
walk yesterday?”, or “How did I sleep last night?”

## Run locally

1. Copy `.env.example` to `.env` if you want to change defaults.
2. In one terminal: `cd backend; python -m venv .venv; .venv\\Scripts\\pip install -r requirements.txt; .venv\\Scripts\\uvicorn app.main:app --reload`
3. In another: `cd frontend; npm install; npm run dev`
4. Open `http://localhost:5173`.

Alternatively run `docker compose up --build`.

## Verify

Run backend tests from `backend`: `python -m pytest`.

The dashboard API is at `GET /api/dashboard`; service health is at `GET /health`.
Phase 2 endpoints include `/api/glucose/latest`, `/api/glucose/history`,
`/api/glucose/range`, `/api/medicines`, `/api/meals`, `/api/activities`, and
`/api/sleep`.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the Phase 1 system and
the planned agent/tool and safety boundaries.
