from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.agents.orchestrator import SugarPathAgent
from app.agents.tools import TOOL_MAP
from app.database import SessionLocal
from app.main import app
from app.models import AgentEvent, GlucoseReading, Medication, Notification
from app.services.events import evaluate_events, list_notifications
from app.services.health import patient_id
from app.services.weekly_report import generate_weekly_report


def tool_call(name: str, arguments: dict) -> dict:
    return {"content": "", "tool_calls": [{"function": {"name": name, "arguments": arguments}}]}


class FakeClient:
    def __init__(self, replies): self.replies = replies
    def chat(self, messages, tools): return self.replies.pop(0)


@pytest.fixture
def db():
    with TestClient(app):
        session = SessionLocal()
        try: yield session
        finally: session.close()


def _clear_events(db):
    db.query(Notification).delete(); db.query(AgentEvent).delete(); db.commit()


def test_medicine_due_and_deduplication_with_fixed_time(db):
    _clear_events(db); now = datetime(2030, 1, 2, 20, 30)
    first = evaluate_events(db, now); second = evaluate_events(db, now)
    assert first["events_created"] >= 1 and first["notifications_created"] >= 1
    assert second == {"events_created": 0, "notifications_created": 0}
    assert any(item.category == "medicine_due" for item in list_notifications(db))


def test_medicine_missed_after_grace_and_not_before(db):
    _clear_events(db)
    before = evaluate_events(db, datetime(2030, 1, 3, 20, 30))
    assert any(item.category == "medicine_due" for item in list_notifications(db))
    _clear_events(db)
    after = evaluate_events(db, datetime(2030, 1, 4, 21, 1))
    assert after["events_created"] >= 1
    assert any(item.category == "medicine_missed" for item in list_notifications(db))


def test_taken_medicine_does_not_create_due_event(db):
    _clear_events(db); med = db.scalar(select(Medication).limit(1)); assert med
    from app.models import MedicationEvent
    db.add(MedicationEvent(medication_id=med.id, timestamp=datetime(2030, 1, 5, 20, 5), status="taken")); db.commit()
    evaluate_events(db, datetime(2030, 1, 5, 20, 30))
    medicine_events = db.scalars(select(AgentEvent).where(AgentEvent.event_type.in_(["medicine_due", "medicine_missed"]))).all()
    assert not any((event.payload or {}).get("time_of_day") == "evening" for event in medicine_events)


def test_glucose_report_notification_api_and_states(db):
    _clear_events(db); patient = patient_id(db)
    db.add(GlucoseReading(patient_id=patient, timestamp=datetime(2030, 1, 6, 12), value_mg_dl=250, trend="Rising", source="test", synthetic=True)); db.commit()
    generate_weekly_report(db, datetime(2030, 1, 1).date())
    evaluate_events(db, datetime(2030, 1, 6, 12, 1))
    items = list_notifications(db); assert any(item.category == "glucose_event" for item in items); assert any(item.category == "weekly_report_ready" for item in items)
    with TestClient(app) as client:
        response = client.get("/api/notifications"); assert response.status_code == 200 and response.json()
        identifier = response.json()[0]["id"]
        assert client.patch(f"/api/notifications/{identifier}/read").json()["status"] == "read"
        assert client.patch(f"/api/notifications/{identifier}/dismiss").json()["status"] == "dismissed"


def test_notification_tool_and_safety_boundary(db):
    _clear_events(db); evaluate_events(db, datetime(2030, 1, 7, 20, 30))
    assert TOOL_MAP["get_notifications"].execute(db, {})["ok"]
    agent = SugarPathAgent(client=FakeClient([tool_call("get_notifications", {}), {"content": "You have one notification to check."}]))
    reply = agent.respond(db, "Do I have anything I need to check?")
    assert reply["status"] == "ok" and "Notifications" in reply["sources_used"]
    assert SugarPathAgent(client=FakeClient([])).respond(db, "Should I increase my Metformin?")["status"] == "safe_boundary"


def test_validated_local_reminder_becomes_one_notification(db):
    _clear_events(db)
    with TestClient(app) as client:
        created = client.post("/api/reminders", json={"reminder_type": "activity", "message": "Remember your evening walk.", "due_at": "2030-01-08T18:00:00"})
        assert created.status_code == 201
    first = evaluate_events(db, datetime(2030, 1, 8, 18, 1)); second = evaluate_events(db, datetime(2030, 1, 8, 18, 1))
    assert first["events_created"] >= 1 and second["events_created"] == 0
    assert any(item.category == "reminder_due" for item in list_notifications(db))
