# Sugar Path architecture

## Scope of the first delivery

Phases 1–2 establish a local, demo-only foundation: a React dashboard and
health-history views read a seeded fictional patient's stored data from a
FastAPI service. A deterministic mock CGM provider returns five-minute
synthetic readings, and validated backend actions can record meals and
medicine confirmations. Ollama and reminders remain later phases.

## System overview

```text
React + Vite client  --HTTP/JSON-->  FastAPI API  -->  SQLAlchemy  --> SQLite
        dashboard                       services        models        local file
```

The frontend is responsible only for accessible presentation and user
interaction. The backend owns patient data, validation, seed data and every
future health-data mutation. SQLite is the default local database; the
`DATABASE_URL` setting permits PostgreSQL without changing application code.

## Components and responsibilities

| Component | Responsibility |
| --- | --- |
| `frontend` | Mobile-first Sugar Path dashboard, loading/error states, and the demo-data disclaimer. |
| `backend/app/api` | Small versioned HTTP surface. Phase 1 exposes health and dashboard summary endpoints. |
| `backend/app/services` | Assembles patient-facing data rather than exposing ORM models directly; contains the mock CGM and local-food service boundaries. |
| `backend/app/models` | Relational persistence models and timestamped health events. |
| `backend/app/seed` | Idempotently creates Rahul Sen and at least 14 days of deterministic synthetic history. |
| `backend/app/safety` | Reserved deterministic safety boundary; future AI never decides risk on its own. |
| `backend/app/tools` | Reserved validated tool layer for future agent reads/writes. |

## Data design

The database contains the domain entities required for the product: users,
patient profiles, medications and schedules/events, glucose readings, meals
and meal items, activity and sleep events, agent memories/events,
notifications and weekly reports. All event records have timestamps.

Phase 1 seeds the records dashboard needs: one demo user/profile, Metformin
schedules/events, glucose readings, meals, activity and sleep. Phase 2's
`MockCGMProvider` fills five-minute API responses with a repeatable daily
curve while labeling every value as synthetic. `DexcomProvider` is a reserved
future adapter, never a simulated external integration.
All generated readings carry `synthetic=true`; the UI must communicate that
they are not clinical data.

## Request flow

1. Browser loads the dashboard.
2. `GET /api/dashboard` loads the latest stored snapshot for the demo patient.
3. The dashboard service queries and derives a concise view model (current
   glucose, today's medicine, last meal, activity and profile).
4. The browser renders it with explicit loading, error and demo states.

For Phase 2 history and actions, the browser calls dedicated endpoints. The
mock CGM provider reads stored readings where available and deterministically
fills five-minute gaps. Meal descriptions are matched to a local food table;
the server—not a language model—calculates nutrition. Medicine confirmation
and meal logging are Pydantic-validated API mutations.

## Future agent and safety boundary

## Phase 3 agent flow

```text
Patient → Ask Sugar Path UI → POST /api/assistant/chat → agent orchestrator
  → Ollama → requested named tool → validated application service/database
  → structured tool result → Ollama → grounded answer → patient
```

The Ollama client is an isolated HTTP adapter configured by `OLLAMA_BASE_URL`
and `OLLAMA_MODEL`. The agent supplies only the system policy, user message,
and JSON schemas for registered tools—not a database dump. It loops for at
most `MAX_TOOL_ITERATIONS` (default 6) and returns the human-readable answer
with source labels for the UI.

The registry separates read tools (glucose, meals, medicine, activity, sleep,
profile and daily summary) from two validated write tools: `log_meal` and
`confirm_medication`. The model has no database session, SQL capability, or
arbitrary mutation capability. Tool errors, unknown tool names, malformed
arguments, unavailable Ollama, and iteration limits all resolve to simple
patient-facing messages and structured logs rather than tracebacks.

Safety rules stay deterministic and independent of the model. Configurable
threshold checks will create UI alerts that direct the patient to their care
plan or qualified clinical help, never dose changes, diagnoses, or model-made
emergency treatment instructions.
