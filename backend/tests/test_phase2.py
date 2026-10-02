from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models import Medication, MedicationEvent, MedicationSchedule, PatientProfile
from app.services.health import medications


def test_mock_cgm_returns_five_minute_history():
    with TestClient(app) as client:
        response = client.get("/api/glucose/history?hours=1")
    assert response.status_code == 200
    assert len(response.json()) >= 12
    assert all(item["synthetic"] for item in response.json())


def test_confirm_medicine_and_log_known_food():
    with TestClient(app) as client:
        medicine = client.get("/api/medicines").json()[0]
        confirmed = client.post(f"/api/medicines/{medicine['id']}/confirm", json={"time_of_day": "morning"})
        meal = client.post("/api/meals", json={"description": "I ate 2 rotis, dal and an egg.", "meal_type": "lunch"})
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "taken"
    assert meal.status_code == 201
    assert meal.json()["estimated_carbs_g"] > 0


def test_yesterdays_medicine_event_does_not_mark_todays_dose_taken():
    """Only medication events from the current calendar day affect today's status."""
    with TestClient(app):
        db = SessionLocal()
        medication = schedule = event = None
        try:
            patient = db.scalars(select(PatientProfile).limit(1)).first()
            assert patient is not None
            medication = Medication(patient_id=patient.id, name="Regression Test Medicine", dose="1 tablet")
            db.add(medication)
            db.flush()
            schedule = MedicationSchedule(medication_id=medication.id, time_of_day="morning", instructions="Test only")
            event = MedicationEvent(medication_id=medication.id, timestamp=datetime.now() - timedelta(days=1), status="taken")
            db.add_all([schedule, event])
            db.commit()

            medicine_status = next(item for item in medications(db) if item.id == medication.id)

            assert medicine_status.time_of_day == "morning"
            assert medicine_status.status == "scheduled"
            assert medicine_status.event_time is None
        finally:
            if event is not None:
                db.delete(event)
            if schedule is not None:
                db.delete(schedule)
            if medication is not None:
                db.delete(medication)
            db.commit()
            db.close()
