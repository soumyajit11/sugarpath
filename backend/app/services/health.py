from datetime import datetime, timedelta
import re
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ActivityEvent, Meal, MealItem, Medication, MedicationEvent, MedicationSchedule, PatientProfile, SleepEvent
from app.schemas.health import ActivityOut, MealOut, MedicationOut, SleepOut

FOODS: dict[str, tuple[float, float, float, float]] = {
    "white rice": (45, 205, 4, 0.4), "brown rice": (40, 216, 5, 1.8), "roti": (18, 105, 3, 3),
    "dal": (20, 180, 10, 4), "chicken curry": (8, 230, 24, 12), "potato curry": (28, 190, 4, 8),
    "banana": (27, 105, 1, 0.4), "apple": (25, 95, 0.5, 0.3), "bread": (14, 80, 3, 1),
    "egg": (1, 72, 6, 5), "milk": (12, 120, 8, 5), "tea": (4, 35, 1, 1),
    "oats": (27, 150, 5, 3), "vegetables": (12, 80, 3, 2),
}


def patient_id(db: Session) -> int:
    profile = db.scalar(select(PatientProfile).limit(1))
    if not profile:
        raise LookupError("Demo patient has not been seeded")
    return profile.id


def medications(db: Session) -> list[MedicationOut]:
    now = datetime.now()
    result: list[MedicationOut] = []
    for med in db.scalars(select(Medication).where(Medication.patient_id == patient_id(db))).all():
        latest = db.scalar(select(MedicationEvent).where(MedicationEvent.medication_id == med.id).order_by(MedicationEvent.timestamp.desc()))
        for schedule in db.scalars(select(MedicationSchedule).where(MedicationSchedule.medication_id == med.id)).all():
            is_upcoming = schedule.time_of_day == "evening" and now.hour < 20
            status = "upcoming" if is_upcoming else (latest.status if latest else "scheduled")
            result.append(MedicationOut(id=med.id, name=med.name, dose=med.dose, time_of_day=schedule.time_of_day, instructions=schedule.instructions, status=status, event_time=None if is_upcoming or not latest else latest.timestamp))
    return result


def confirm_medication(db: Session, medication_id: int, time_of_day: str) -> MedicationOut:
    med = db.get(Medication, medication_id)
    if med is None or med.patient_id != patient_id(db):
        raise ValueError("Medicine was not found")
    schedule = db.scalar(select(MedicationSchedule).where(MedicationSchedule.medication_id == med.id, MedicationSchedule.time_of_day == time_of_day))
    if schedule is None:
        raise ValueError("Medicine schedule was not found")
    event = MedicationEvent(medication_id=med.id, timestamp=datetime.now(), status="taken")
    db.add(event); db.commit(); db.refresh(event)
    return MedicationOut(id=med.id, name=med.name, dose=med.dose, time_of_day=time_of_day, instructions=schedule.instructions, status="taken", event_time=event.timestamp)


def meal_out(db: Session, meal: Meal) -> MealOut:
    items = db.scalars(select(MealItem).where(MealItem.meal_id == meal.id)).all()
    return MealOut(id=meal.id, timestamp=meal.timestamp, meal_type=meal.meal_type, description=meal.description, estimated_carbs_g=meal.estimated_carbs_g, calories=meal.calories, protein_g=meal.protein_g, fat_g=meal.fat_g, items=[f"{item.quantity} {item.name}" for item in items], source=meal.source)


def list_meals(db: Session, days: int = 7) -> list[MealOut]:
    cutoff = datetime.now() - timedelta(days=days)
    rows = db.scalars(select(Meal).where(Meal.patient_id == patient_id(db), Meal.timestamp >= cutoff).order_by(Meal.timestamp.desc())).all()
    return [meal_out(db, row) for row in rows]


def log_meal(db: Session, description: str, meal_type: str) -> MealOut:
    lower = description.lower()
    matched = [(name, values) for name, values in FOODS.items() if name in lower]
    if not matched:
        raise ValueError("We could not identify a food in that meal. Try a common food such as roti, dal, egg, oats, or rice.")
    totals = [sum(values[index] for _, values in matched) for index in range(4)]
    meal = Meal(patient_id=patient_id(db), timestamp=datetime.now(), meal_type=meal_type, description=description.strip(), estimated_carbs_g=totals[0], calories=totals[1], protein_g=totals[2], fat_g=totals[3], source="local_food_dataset")
    db.add(meal); db.flush()
    for name, _ in matched:
        quantity = "1 serving"
        match = re.search(rf"(\d+)\s+{re.escape(name)}", lower)
        if match: quantity = f"{match.group(1)} servings"
        db.add(MealItem(meal_id=meal.id, name=name, quantity=quantity))
    db.commit(); db.refresh(meal)
    return meal_out(db, meal)


def activities(db: Session, days: int = 7) -> list[ActivityOut]:
    rows = db.scalars(select(ActivityEvent).where(ActivityEvent.patient_id == patient_id(db), ActivityEvent.timestamp >= datetime.now() - timedelta(days=days)).order_by(ActivityEvent.timestamp.desc())).all()
    return [ActivityOut(timestamp=row.timestamp, activity_type=row.activity_type, duration_minutes=row.duration_minutes, steps=row.steps) for row in rows]


def sleep(db: Session, days: int = 7) -> list[SleepOut]:
    rows = db.scalars(select(SleepEvent).where(SleepEvent.patient_id == patient_id(db), SleepEvent.end_time >= datetime.now() - timedelta(days=days)).order_by(SleepEvent.end_time.desc())).all()
    return [SleepOut(start_time=row.start_time, end_time=row.end_time, quality=row.quality, duration_minutes=round((row.end_time - row.start_time).total_seconds() / 60)) for row in rows]
