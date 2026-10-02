from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ActivityEvent, GlucoseReading, Meal, Medication, MedicationEvent, MedicationSchedule, PatientProfile, User
from app.schemas.dashboard import ActivityCard, DashboardResponse, GlucoseCard, MealCard, MedicineCard


def get_dashboard(db: Session) -> DashboardResponse:
    now = datetime.now()
    profile = db.scalar(select(PatientProfile).limit(1))
    if profile is None:
        raise LookupError("Demo patient has not been seeded")
    user = db.get(User, profile.user_id)
    glucose = db.scalar(select(GlucoseReading).where(GlucoseReading.patient_id == profile.id, GlucoseReading.timestamp <= now).order_by(GlucoseReading.timestamp.desc()))
    meal = db.scalar(select(Meal).where(Meal.patient_id == profile.id, Meal.timestamp <= now).order_by(Meal.timestamp.desc()))
    activity = db.scalar(select(ActivityEvent).where(ActivityEvent.patient_id == profile.id, ActivityEvent.timestamp <= now).order_by(ActivityEvent.timestamp.desc()))
    medications = db.scalars(select(Medication).where(Medication.patient_id == profile.id)).all()

    medicine_cards = []
    for medication in medications:
        schedules = db.scalars(select(MedicationSchedule).where(MedicationSchedule.medication_id == medication.id)).all()
        for schedule in schedules:
            # The Phase 1 schema has a medication-level event. A later phase will
            # associate events to their individual schedules. Until then, don't
            # present an evening dose as missed before its scheduled evening time.
            if schedule.time_of_day == "evening" and now.hour < 20:
                medicine_cards.append(MedicineCard(label="Evening medicine", detail="Due at 9:00 PM", status="upcoming"))
                continue
            event = db.scalar(select(MedicationEvent).where(MedicationEvent.medication_id == medication.id, MedicationEvent.timestamp <= now).order_by(MedicationEvent.timestamp.desc()))
            if event and event.status == "taken":
                detail, status = f"Taken at {event.timestamp.strftime('%I:%M %p').lstrip('0')}", "taken"
            else:
                detail, status = f"Due {schedule.time_of_day}", "upcoming"
            medicine_cards.append(MedicineCard(label=f"{schedule.time_of_day.title()} medicine", detail=detail, status=status))

    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    return DashboardResponse(
        patient_name=user.name,
        greeting=f"{greeting}, {user.name.split()[0]}",
        glucose=GlucoseCard(value_mg_dl=glucose.value_mg_dl, trend=glucose.trend or "Stable", updated_at=glucose.timestamp, synthetic=glucose.synthetic),
        medicines=medicine_cards,
        last_meal=MealCard(description=meal.description, meal_type=meal.meal_type, timestamp=meal.timestamp, carbs_g=meal.estimated_carbs_g),
        activity=ActivityCard(description=f"{activity.activity_type.title()} today", duration_minutes=activity.duration_minutes, steps=activity.steps),
        demo_mode=True,
    )
