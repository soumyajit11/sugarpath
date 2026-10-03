# Sugar Path demo flow

This reliable 5–7 minute walkthrough uses the fictional patient and synthetic data.

1. Show **Dashboard**: current glucose, medicine, activity, and latest meal.
2. Open **Glucose** and switch among the synthetic 24-hour, 3-day, and 7-day views.
3. Open **Medicine** and confirm a scheduled dose; explain confirmation is idempotent for its schedule slot.
4. In **Ask Sugar Path**, ask: “How much did I walk yesterday?” Explain that a typed activity tool retrieves data.
5. Ask: “Remember that I usually eat breakfast at 8 AM.” Then ask when breakfast is usually eaten; show the inspectable/removable **Memory** entry.
6. Open **Weekly Report**. Explain that metrics are deterministic Python calculations, not model calculations.
7. Open **Notifications**, choose **Check now** twice, and show deduplication.
8. Ask: “Should I take extra Metformin because my glucose is high?” Show the deterministic safety refusal before any model call.

If Ollama is unavailable, skip the chat interactions and show its controlled unavailable state; all other steps work.

## Safe local demo reset

Stop the backend. Only when `DEMO_MODE=true` and `DATABASE_URL` is the default local SQLite database, remove `backend/sugar_path.db`, then restart the backend to reseed. Do not apply this to a shared or non-demo database.
