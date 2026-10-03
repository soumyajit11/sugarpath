# Sugar Path

Sugar Path is a local, demo-only diabetes companion prototype. It uses a
fictional patient and synthetic health data; it is not medical software and
does not provide diagnosis, emergency care, or dosing advice.

## Current scope: Phases 1–4

The current implementation provides a FastAPI + SQLite backend that seeds
Rahul Sen with 15 days of synthetic readings and daily events, plus a
mobile-first React dashboard. It includes a deterministic five-minute Mock CGM
feed, glucose graph, medicine confirmation, natural-language meal logging
using only a local food table, activity/sleep history views, and the completed
Phase 3 Ask Sugar Path assistant. Weekly reporting, persistent memory, and
notifications remain later phases.

## What Sugar Path remembers

Phase 4 adds patient-controlled, structured long-term memory: routines, preferences, explicitly provided patient facts, and clearly labeled derived observations. Memory is a small, inspectable SQLite record—not a chat transcript. Patients can view and remove memories on the **Memory** page; each item shows its patient-friendly category, source, and update date.

The assistant retrieves only relevant memories through validated tools and stores a memory only for an explicit “remember…” request. Medication instructions, diagnoses, dose changes, and treatment instructions are rejected, and the deterministic safety boundary always runs first. Normalized duplicates are prevented for the same patient and category.

No vector database, embeddings, RAG, LangChain, or LangGraph is used: this small structured memory set uses deterministic category and keyword retrieval.

## Ask Sugar Path and Ollama

`backend/app/config.py` automatically loads a root `.env` file. Configure a
locally installed tool-calling model, for example:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
OLLAMA_TIMEOUT_SECONDS=120
MAX_TOOL_ITERATIONS=10
```

Start Ollama, pull the configured model, then start Sugar Path:

```powershell
ollama serve
ollama pull llama3.2:3b
```

Phase 3 was verified against `llama3.2:3b` at `http://localhost:11434` using
real `/api/chat` tool calls. Sugar Path sends the configured model only the
patient question, safety policy, and explicit tool schemas—not a database dump.
The model can request structured backend tools for glucose, meals, medicine,
activity, sleep, profile, daily summaries, highest-glucose meal context, and
morning glucose context. Validated tools are the only way it can read or write
application data, and each turn is capped at `MAX_TOOL_ITERATIONS=10`.

Medication or insulin dose-change requests are handled by a deterministic
safety boundary before the model is called; Sugar Path does not recommend dose
changes.

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
Memory is available at `GET/POST /api/memories`, `PATCH /api/memories/{memory_id}`, and `DELETE /api/memories/{memory_id}`.
Phase 2 endpoints include `/api/glucose/latest`, `/api/glucose/history`,
`/api/glucose/range`, `/api/medicines`, `/api/meals`, `/api/activities`, and
`/api/sleep`. Phase 3 adds `POST /api/assistant/chat`.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the completed Phase 1–3
system and its local Ollama tool-calling and safety boundaries.
