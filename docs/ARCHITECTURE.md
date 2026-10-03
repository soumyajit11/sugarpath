# Sugar Path architecture

## Current delivery scope: Phases 1–6

Phases 1–3 establish a local, demo-only foundation: a React dashboard and
health-history views read a seeded fictional patient's stored data from a
FastAPI service. A deterministic mock CGM provider returns five-minute
synthetic readings, validated backend actions can record meals and medicine
confirmations, and the Phase 3 assistant uses a local Ollama model through
real, validated tool calls. Semantic memory, weekly reports, notifications,
and external integrations remain later phases.

Phase 4 implements only persistent structured memory; it does not implement reports or notifications.

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
| `backend/app/api` | Small HTTP surface for dashboard, health-data, and `POST /api/assistant/chat` endpoints. |
| `backend/app/services` | Assembles patient-facing data rather than exposing ORM models directly; contains the mock CGM and local-food service boundaries. |
| `backend/app/models` | Relational persistence models and timestamped health events. |
| `backend/app/seed` | Idempotently creates Rahul Sen and at least 14 days of deterministic synthetic history. |
| `backend/app/safety` | Active deterministic safety boundary for medication dose-change requests; the model never decides that risk. |
| `backend/app/agents` | Phase 3 agent orchestrator, Ollama adapter, and validated tool registry for agent reads/writes. |

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

## Phase 3 agent and safety boundary

### Phase 3 agent flow

```text
Patient → Ask Sugar Path UI → POST /api/assistant/chat → agent orchestrator
  → Ollama → requested named tool → validated application service/database
  → structured tool result → Ollama → grounded answer → patient
```

The Ollama client is an isolated HTTP adapter configured by `OLLAMA_BASE_URL`
and `OLLAMA_MODEL`. The agent supplies only the system policy, user message,
and JSON schemas for registered tools—not a database dump. It loops for at
most `MAX_TOOL_ITERATIONS` (default 10) and returns the human-readable answer
with source labels for the UI.

The registry separates read tools (glucose, meals, medicine, activity, sleep,
profile, daily summary, highest-glucose meal context, and morning glucose
context) from two validated write tools: `log_meal` and `confirm_medication`.
The model has no database session, SQL capability, or arbitrary mutation
capability. Tool errors, unknown tool names, malformed arguments, unavailable
Ollama, and iteration limits all resolve to simple patient-facing messages and
structured logs rather than tracebacks.

Safety rules stay deterministic and independent of the model. Medication or
insulin dose-change requests are intercepted before a model call and receive a
safe advisory directing the patient to their care plan or qualified clinical
help. Proactive threshold alerts, persistent memory, reports, and notifications
are not part of the current delivery.

## Phase 4 structured memory

`AgentMemory` persists a patient-specific record with `memory_type`, `content`, `source`, and timestamps in the existing SQLite/SQLAlchemy database. Approved categories are routines, preferences, patient facts explicitly supplied by the patient, and clearly labeled system observations. Sources are an explicit request, a confirmed request, or observed Sugar Path data.

The memory service is the only standard application path that creates, updates, deletes, deduplicates, or retrieves records. Pydantic validates API and tool inputs. It normalizes duplicate content per patient/category and rejects medical instructions, diagnoses, dose changes, and treatment instructions. Complete chat transcripts are never written as memory.

The agent has validated `get_agent_memories` and constrained `store_agent_memory` tools. It retrieves only relevant memories through small deterministic keyword/category filters, and stores only explicit “remember” requests. The deterministic safety policy runs before the agent and remains higher priority than memory.

`GET /api/memories`, `POST /api/memories`, `PATCH /api/memories/{memory_id}`, and `DELETE /api/memories/{memory_id}` provide transparent control. The Memory page shows friendly labels, source wording, last update, and removal. No vector database, embeddings, RAG, LangChain, or LangGraph is needed for this small structured set.

## Phase 5 weekly analytics and reports

The weekly-report service uses seven local calendar days and queries stored records directly. It deterministically derives glucose count, average, extrema/timestamps, daily and morning averages, and prototype excursion counts; medication scheduled/taken/missed/skipped totals and adherence; meal counts and carbohydrates; activity minutes/steps/days; and sleep duration/quality counts. The model is never given raw CGM readings to calculate these values.

Small pattern rules are explainable and evidence-counted rather than machine-learned: a morning-versus-evening missed-medicine difference or an activity/glucose association is emitted only when its data requirements are met. Otherwise the report says that no consistent pattern was found. These are observational descriptions, never causal claims or treatment guidance. Clinician questions are deterministic discussion prompts only.

`WeeklyReport.content` stores the patient-facing deterministic fallback narrative and `structured_data` stores the typed compact JSON summary. A startup-compatible SQLite migration adds the JSON column for existing prototype databases. Generating the same patient/week updates its report. `GET /api/reports/weekly/current`, `POST /api/reports/weekly/generate`, and `GET /api/reports/weekly/{report_id}` expose reports; `get_weekly_summary` gives the agent only the compact result.

The React Weekly Report page is mobile-friendly, marked “Demo data only,” and includes browser print/save-as-PDF styling. Reports work without Ollama through the deterministic narrative fallback. Phase 6 adds local in-app events only; production scheduling and external delivery remain out of scope.

## Phase 6 local event engine and notifications

The local event engine is explicitly triggered through `POST /api/events/evaluate`; it has no production scheduler, external delivery provider, or model dependency. The evaluator accepts an injected `now` timestamp internally for deterministic tests. It evaluates finite categories only: `medicine_due`, `medicine_missed`, `weekly_report_ready`, `glucose_event`, and reserved `reminder_due`.

Each event has a persisted deterministic key made from the patient, event condition, date, and related entity. Re-running evaluation finds the same key and skips it. Pending events are converted to exactly one notification through an event link, then receive `processed_at`. Notification statuses are `unread`, `read`, and `dismissed` and are controlled through the API, not the model.

Medicine timing uses configured local demo hours and `MEDICINE_MISSED_GRACE_MINUTES`; a recorded taken/skipped event prevents that schedule slot from notifying. Glucose checks compare the latest stored synthetic reading with `GLUCOSE_LOW_THRESHOLD` and `GLUCOSE_HIGH_THRESHOLD`, which are explicitly prototype/demo thresholds—not clinical judgement. Weekly-report-ready events are created when a report is generated or refreshed.

The Notification center and dashboard bell provide readable in-app updates and contextual links to medicine, glucose, or weekly-report pages. `get_notifications` lets Ask Sugar Path summarize persisted unread notifications only. The event system never asks Ollama whether an event is important, never changes medication or insulin, and never sends email, SMS, push, WhatsApp, or external messages.

Validated local reminder records support medicine, activity, meal-logging, and custom categories through `POST /api/reminders`; due reminders become `reminder_due` events on the next explicit evaluation. The frontend never creates raw events or arbitrary event payloads.

## Phase 7 presentation layer

Phase 7 keeps the API and backend architecture unchanged while splitting the frontend shell into a reusable `components/AppShell` and page header. The shell presents five primary mobile destinations (Home, Glucose, Medicine, Ask, and More), a responsive desktop sidebar, a notification bell, and a shared token-based CSS visual system. Page components continue to use local React state and the existing API client; no global state library or UI framework was introduced.
