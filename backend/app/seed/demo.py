from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ActivityEvent, GlucoseReading, Meal, Medication, MedicationEvent, MedicationSchedule, PatientProfile, SleepEvent, User


def seed_demo_data(db: Session) -> None:
    if db.scalar(select(User).where(User.email == "rahul.sen@example.demo")):
        return
    now = datetime.now().replace(second=0, microsecond=0)
    user = User(name="Rahul Sen", email="rahul.sen@example.demo")
    db.add(user); db.flush()
    patient = PatientProfile(user_id=user.id, age=46, condition="Type 2 Diabetes", typical_breakfast_time="8:00 AM", typical_dinner_time="9:00 PM", typical_walk_minutes=30)
    db.add(patient); db.flush()
    medication = Medication(patient_id=patient.id, name="Metformin", dose="500 mg")
    db.add(medication); db.flush()
    db.add_all([
        MedicationSchedule(medication_id=medication.id, time_of_day="morning", instructions="After breakfast"),
        MedicationSchedule(medication_id=medication.id, time_of_day="evening", instructions="After dinner"),
    ])
    for day in range(14, -1, -1):
        date = now - timedelta(days=day)
        breakfast = date.replace(hour=8, minute=0)
        dinner = date.replace(hour=21, minute=0)
        db.add_all([
            Meal(patient_id=patient.id, timestamp=breakfast, meal_type="breakfast", description="Oats with milk and banana", estimated_carbs_g=48, calories=340, protein_g=12, fat_g=8),
            Meal(patient_id=patient.id, timestamp=dinner, meal_type="dinner", description="2 rotis, dal and vegetables", estimated_carbs_g=52, calories=480, protein_g=18, fat_g=12),
            MedicationEvent(medication_id=medication.id, timestamp=breakfast + timedelta(minutes=12), status="taken"),
            MedicationEvent(medication_id=medication.id, timestamp=dinner + timedelta(minutes=10), status="taken" if day % 5 else "missed"),
            ActivityEvent(patient_id=patient.id, timestamp=date.replace(hour=18, minute=30), activity_type="walk", duration_minutes=30, steps=3900 + day * 20),
            SleepEvent(patient_id=patient.id, start_time=(date - timedelta(days=1)).replace(hour=23, minute=0), end_time=date.replace(hour=6, minute=30), quality="fair"),
        ])
        for index in range(0, 288, 12):
            timestamp = date.replace(hour=0, minute=0) + timedelta(minutes=index * 5)
            meal_bump = 28 if timestamp.hour in (8, 9) else 22 if timestamp.hour in (21, 22) else 0
            value = 108 + ((day * 7 + index * 3) % 18) + meal_bump
            db.add(GlucoseReading(patient_id=patient.id, timestamp=timestamp, value_mg_dl=value, trend="Stable" if index % 24 else "Rising", source="mock_cgm", synthetic=True))
    # A current reading ensures the dashboard makes sense whenever the seed is run.
    db.add(GlucoseReading(patient_id=patient.id, timestamp=now, value_mg_dl=118, trend="Stable", source="mock_cgm", synthetic=True))
    db.commit()
