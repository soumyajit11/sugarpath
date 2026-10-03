from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ActivityEvent, AgentMemory, GlucoseReading, Meal, Medication, MedicationEvent, MedicationSchedule, SleepEvent, WeeklyReport
from app.schemas.weekly_report import ActivityWeekly, GlucoseWeekly, MealsWeekly, MedicineWeekly, ObservedPattern, SleepWeekly, WeeklyReportOut, WeeklySummary
from app.services.health import patient_id

HIGH_EXCURSION = 180
LOW_EXCURSION = 70
LATE_MEAL_HOUR = 21


def current_week_start(now: datetime | None = None) -> date:
    today = (now or datetime.now()).date()
    return today - timedelta(days=6)


def _bounds(start: date) -> tuple[datetime, datetime]:
    begin = datetime.combine(start, time.min)
    return begin, begin + timedelta(days=7)


def build_weekly_summary(db: Session, week_start: date | None = None, patient: int | None = None) -> WeeklySummary:
    start = week_start or current_week_start(); begin, end = _bounds(start); patient = patient or patient_id(db)
    readings = list(db.scalars(select(GlucoseReading).where(GlucoseReading.patient_id == patient, GlucoseReading.timestamp >= begin, GlucoseReading.timestamp < end).order_by(GlucoseReading.timestamp)).all())
    values = [row.value_mg_dl for row in readings]
    high = max(readings, key=lambda row: row.value_mg_dl) if readings else None; low = min(readings, key=lambda row: row.value_mg_dl) if readings else None
    days: dict[str, list[int]] = defaultdict(list); mornings: list[int] = []
    for row in readings:
        days[row.timestamp.date().isoformat()].append(row.value_mg_dl)
        if 5 <= row.timestamp.hour < 12: mornings.append(row.value_mg_dl)
    glucose = GlucoseWeekly(reading_count=len(readings), average_mg_dl=round(sum(values) / len(values)) if values else None, minimum_mg_dl=low.value_mg_dl if low else None, maximum_mg_dl=high.value_mg_dl if high else None, highest_at=high.timestamp if high else None, lowest_at=low.timestamp if low else None, daily_averages={day: round(sum(items) / len(items)) for day, items in days.items()}, morning_average_mg_dl=round(sum(mornings) / len(mornings)) if mornings else None, excursions_high=sum(value >= HIGH_EXCURSION for value in values), excursions_low=sum(value <= LOW_EXCURSION for value in values))

    meds = list(db.scalars(select(Medication).where(Medication.patient_id == patient)).all()); med_ids = [med.id for med in meds]
    schedules = list(db.scalars(select(MedicationSchedule).where(MedicationSchedule.medication_id.in_(med_ids))).all()) if med_ids else []
    events = list(db.scalars(select(MedicationEvent).where(MedicationEvent.medication_id.in_(med_ids), MedicationEvent.timestamp >= begin, MedicationEvent.timestamp < end)).all()) if med_ids else []
    expected = len(schedules) * 7
    # Repeated UI confirmations are possible in a prototype. For adherence,
    # count only the latest recorded event for each medicine/day/schedule slot.
    latest_events: dict[tuple[int, date, str], MedicationEvent] = {}
    for event in events:
        slot = "morning" if event.timestamp.hour < 15 else "evening"
        key = (event.medication_id, event.timestamp.date(), slot)
        if key not in latest_events or event.timestamp > latest_events[key].timestamp:
            latest_events[key] = event
    status_counts = Counter(event.status for event in latest_events.values()); slots = {"morning": Counter(), "evening": Counter()}
    for event in latest_events.values(): slots["morning" if event.timestamp.hour < 15 else "evening"][event.status] += 1
    taken = status_counts["taken"]; missed = status_counts["missed"]; skipped = status_counts["skipped"]
    medicine = MedicineWeekly(scheduled_doses=expected, taken_doses=taken, missed_doses=missed, skipped_doses=skipped, adherence_percent=round(taken / expected * 100, 1) if expected else None, morning={"taken": slots["morning"]["taken"], "missed": slots["morning"]["missed"]}, evening={"taken": slots["evening"]["taken"], "missed": slots["evening"]["missed"]})

    meals = list(db.scalars(select(Meal).where(Meal.patient_id == patient, Meal.timestamp >= begin, Meal.timestamp < end).order_by(Meal.estimated_carbs_g.desc())).all())
    descriptions = Counter(meal.description for meal in meals)
    meal_summary = MealsWeekly(logged_meals=len(meals), average_carbs_g=round(sum(meal.estimated_carbs_g for meal in meals) / len(meals), 1) if meals else None, late_meals=sum(meal.timestamp.hour >= LATE_MEAL_HOUR for meal in meals), recurring_meals=[name for name, count in descriptions.items() if count >= 2][:3], highest_carb_meals=[{"description": meal.description, "carbs_g": meal.estimated_carbs_g, "at": meal.timestamp} for meal in meals[:3]])

    activities = list(db.scalars(select(ActivityEvent).where(ActivityEvent.patient_id == patient, ActivityEvent.timestamp >= begin, ActivityEvent.timestamp < end)).all())
    active_days = {event.timestamp.date() for event in activities}; total_minutes = sum(event.duration_minutes for event in activities); total_steps = sum(event.steps or 0 for event in activities)
    activity = ActivityWeekly(total_minutes=total_minutes, average_minutes_per_day=round(total_minutes / 7, 1), total_steps=total_steps, average_steps_per_day=round(total_steps / 7), active_days=len(active_days))

    sleeps = list(db.scalars(select(SleepEvent).where(SleepEvent.patient_id == patient, SleepEvent.end_time >= begin, SleepEvent.end_time < end)).all())
    durations = [round((event.end_time - event.start_time).total_seconds() / 60) for event in sleeps]
    sleep_summary = SleepWeekly(nights_recorded=len(sleeps), average_duration_minutes=round(sum(durations) / len(durations)) if durations else None, shortest_minutes=min(durations) if durations else None, longest_minutes=max(durations) if durations else None, quality_counts=dict(Counter(event.quality or "Not recorded" for event in sleeps)))

    patterns: list[ObservedPattern] = []
    if medicine.evening["missed"] > medicine.morning["missed"]:
        patterns.append(ObservedPattern(description="Evening medicine was missed more often than morning medicine this week.", matching_days=medicine.evening["missed"], observed_days=7))
    daily_glucose = {date.fromisoformat(key): value for key, value in glucose.daily_averages.items()}
    activity_by_day: dict[date, int] = defaultdict(int)
    for event in activities: activity_by_day[event.timestamp.date()] += event.duration_minutes
    active_glucose = [daily_glucose[day] for day, minutes in activity_by_day.items() if minutes >= 30 and day in daily_glucose]
    inactive_glucose = [value for day, value in daily_glucose.items() if activity_by_day.get(day, 0) < 30]
    if len(active_glucose) >= 2 and len(inactive_glucose) >= 2 and sum(inactive_glucose) / len(inactive_glucose) >= sum(active_glucose) / len(active_glucose) + 10:
        patterns.append(ObservedPattern(description="Lower-activity days were associated with higher average glucose this week.", matching_days=len(inactive_glucose), observed_days=len(daily_glucose)))
    questions: list[str] = []
    if glucose.morning_average_mg_dl and glucose.morning_average_mg_dl >= 140: questions.append("I noticed higher morning glucose on several days. Is this worth discussing?")
    if missed: questions.append(f"I missed medicine {missed} time{'s' if missed != 1 else ''} this week. What strategies would you recommend to improve adherence?")
    if not questions: questions.append("Is there anything in this weekly summary that would be useful to discuss at my next visit?")
    preferences = [memory.content for memory in db.scalars(select(AgentMemory).where(AgentMemory.patient_id == patient, AgentMemory.memory_type == "preference")).all()]
    return WeeklySummary(week_start=start, week_end=start + timedelta(days=6), glucose=glucose, medicine=medicine, meals=meal_summary, activity=activity, sleep=sleep_summary, patterns=patterns, questions_for_clinician=questions, relevant_preferences=preferences)


def fallback_narrative(summary: WeeklySummary) -> str:
    lines = [f"Sugar Path Weekly Summary ({summary.week_start:%b %d} to {summary.week_end:%b %d})", "Demo data only — this is not clinical advice."]
    lines.append(f"Glucose: {summary.glucose.reading_count} readings; average {summary.glucose.average_mg_dl or 'not available'} mg/dL.")
    adherence = f"{summary.medicine.adherence_percent}%" if summary.medicine.adherence_percent is not None else "not available"
    lines.append(f"Medicine: {summary.medicine.taken_doses} taken, {summary.medicine.missed_doses} missed; adherence {adherence}.")
    lines.append(f"Meals: {summary.meals.logged_meals} logged; average estimated carbohydrates {summary.meals.average_carbs_g or 'not available'} g.")
    lines.append(f"Activity: {summary.activity.total_minutes} minutes across {summary.activity.active_days} days.")
    sleep = summary.sleep.average_duration_minutes; lines.append(f"Sleep: {summary.sleep.nights_recorded} nights recorded; average {sleep // 60}h {sleep % 60}m." if sleep is not None else "Sleep: no nights recorded.")
    lines.append(summary.patterns[0].description if summary.patterns else "Patterns noticed: No consistent pattern was found this week.")
    return "\n".join(lines)


def generate_weekly_report(db: Session, week_start: date | None = None) -> WeeklyReportOut:
    summary = build_weekly_summary(db, week_start); patient = patient_id(db); start_dt = datetime.combine(summary.week_start, time.min)
    report = db.scalar(select(WeeklyReport).where(WeeklyReport.patient_id == patient, WeeklyReport.week_start == start_dt))
    narrative = fallback_narrative(summary)
    if report is None:
        report = WeeklyReport(patient_id=patient, week_start=start_dt, content=narrative, structured_data=summary.model_dump(mode="json")); db.add(report)
    else:
        report.content = narrative; report.structured_data = summary.model_dump(mode="json")
    db.commit(); db.refresh(report)
    return WeeklyReportOut(id=report.id, patient_id=report.patient_id, week_start=summary.week_start, generated_at=report.updated_at, summary=summary, narrative=report.content)


def get_weekly_report(db: Session, report_id: int) -> WeeklyReportOut:
    report = db.get(WeeklyReport, report_id)
    if not report: raise LookupError("Weekly report not found.")
    return WeeklyReportOut(id=report.id, patient_id=report.patient_id, week_start=report.week_start.date(), generated_at=report.updated_at, summary=WeeklySummary.model_validate(report.structured_data), narrative=report.content)


def current_weekly_report(db: Session) -> WeeklyReportOut:
    return generate_weekly_report(db, current_week_start())
