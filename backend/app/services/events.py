"""Local deterministic event evaluation; no model or external delivery is involved."""
from datetime import datetime, timedelta
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AgentEvent, GlucoseReading, Medication, MedicationEvent, MedicationSchedule, Notification, Reminder, WeeklyReport
from app.services.health import patient_id

logger = logging.getLogger(__name__)
EVENT_TYPES = {"medicine_due", "medicine_missed", "weekly_report_ready", "glucose_event", "reminder_due"}


def _event_once(db: Session, patient: int, event_type: str, event_key: str, payload: dict) -> tuple[AgentEvent, bool]:
    existing = db.scalar(select(AgentEvent).where(AgentEvent.event_key == event_key))
    if existing:
        logger.info("event_duplicate_skipped event_type=%s", event_type)
        return existing, False
    event = AgentEvent(patient_id=patient, event_type=event_type, event_key=event_key, payload=payload)
    db.add(event); db.flush(); logger.info("event_created event_type=%s", event_type)
    return event, True


def _slot_hour(slot: str) -> int:
    return settings.medicine_morning_due_hour if slot == "morning" else settings.medicine_evening_due_hour


def evaluate_medicine_events(db: Session, now: datetime, patient: int | None = None) -> int:
    patient = patient or patient_id(db); created = 0
    meds = list(db.scalars(select(Medication).where(Medication.patient_id == patient)).all())
    for med in meds:
        schedules = list(db.scalars(select(MedicationSchedule).where(MedicationSchedule.medication_id == med.id)).all())
        for schedule in schedules:
            slot = schedule.time_of_day
            if slot not in {"morning", "evening"}: continue
            due_at = now.replace(hour=_slot_hour(slot), minute=0, second=0, microsecond=0)
            if now < due_at: continue
            events = list(db.scalars(select(MedicationEvent).where(MedicationEvent.medication_id == med.id, MedicationEvent.timestamp >= due_at.replace(hour=0), MedicationEvent.timestamp <= now)).all())
            slot_events = [event for event in events if (event.timestamp.hour < 15) == (slot == "morning")]
            if any(event.status in {"taken", "skipped"} for event in slot_events): continue
            date_key = now.date().isoformat(); base = f"patient_{patient}:med_{med.id}:{slot}:{date_key}"
            event_type = "medicine_missed" if now >= due_at + timedelta(minutes=settings.medicine_missed_grace_minutes) else "medicine_due"
            event_key = f"{event_type}:{base}"
            # A due dose which passes its grace period is one evolving
            # condition, not a second notification-worthy condition.
            prior_due = db.scalar(select(AgentEvent).where(AgentEvent.event_key == f"medicine_due:{base}"))
            if event_type == "medicine_missed" and prior_due:
                prior_due.event_type, prior_due.event_key = event_type, event_key
                prior_due.payload = {"medication_id": med.id, "time_of_day": slot, "date": date_key}
                # It may already have been delivered as a due notification on
                # a prior evaluator run; keep that one record truthful.
                notification = db.scalar(select(Notification).where(Notification.event_id == prior_due.id))
                if notification:
                    notification.category = "medicine_missed"
                    notification.message = f"You have not logged your {slot} medicine."
                was_created = False
            else:
                _, was_created = _event_once(db, patient, event_type, event_key, {"medication_id": med.id, "time_of_day": slot, "date": date_key})
            created += int(was_created)
    return created


def evaluate_glucose_events(db: Session, now: datetime, patient: int | None = None) -> int:
    patient = patient or patient_id(db); created = 0
    readings = db.scalars(select(GlucoseReading).where(GlucoseReading.patient_id == patient, GlucoseReading.timestamp <= now).order_by(GlucoseReading.timestamp.desc()).limit(1)).all()
    for reading in readings:
        direction = "low" if reading.value_mg_dl <= settings.glucose_low_threshold else "high" if reading.value_mg_dl >= settings.glucose_high_threshold else None
        if direction:
            _, was_created = _event_once(db, patient, "glucose_event", f"glucose_event:patient_{patient}:reading_{reading.id}:{direction}", {"reading_id": reading.id, "direction": direction, "value_mg_dl": reading.value_mg_dl})
            created += int(was_created)
    return created


def evaluate_weekly_report_events(db: Session, patient: int | None = None) -> int:
    patient = patient or patient_id(db); created = 0
    reports = db.scalars(select(WeeklyReport).where(WeeklyReport.patient_id == patient)).all()
    for report in reports:
        _, was_created = _event_once(db, patient, "weekly_report_ready", f"weekly_report_ready:patient_{patient}:report_{report.id}", {"report_id": report.id})
        created += int(was_created)
    return created


def evaluate_reminder_events(db: Session, now: datetime, patient: int | None = None) -> int:
    patient = patient or patient_id(db); created = 0
    reminders = db.scalars(select(Reminder).where(Reminder.patient_id == patient, Reminder.status == "active", Reminder.due_at <= now)).all()
    for reminder in reminders:
        _, was_created = _event_once(db, patient, "reminder_due", f"reminder_due:patient_{patient}:reminder_{reminder.id}", {"reminder_id": reminder.id, "reminder_type": reminder.reminder_type, "message": reminder.message})
        created += int(was_created)
    return created


def process_pending_agent_events(db: Session, now: datetime) -> int:
    notifications = 0
    pending = db.scalars(select(AgentEvent).where(AgentEvent.processed_at.is_(None))).all()
    for event in pending:
        try:
            payload = event.payload or {}; slot = payload.get("time_of_day", "medicine")
            messages = {"medicine_due": f"Your {slot} medicine is due.", "medicine_missed": f"You have not logged your {slot} medicine.", "weekly_report_ready": "Your Sugar Path weekly summary is ready.", "glucose_event": "Your glucose reading is outside your configured demo range.", "reminder_due": "You have a Sugar Path reminder to check."}
            notification = db.scalar(select(Notification).where(Notification.event_id == event.id))
            if not notification:
                db.add(Notification(patient_id=event.patient_id, message=messages[event.event_type], category=event.event_type, event_id=event.id, status="unread")); notifications += 1
                logger.info("notification_created category=%s", event.event_type)
            elif notification.category != event.event_type:
                notification.category = event.event_type
                notification.message = messages[event.event_type]
            event.processed_at = now
        except Exception:
            logger.exception("event_processing_failed event_id=%s", event.id)
    return notifications


def evaluate_events(db: Session, now: datetime | None = None) -> dict[str, int]:
    now = now or datetime.now(); logger.info("event_evaluation_started")
    try:
        created = evaluate_medicine_events(db, now) + evaluate_glucose_events(db, now) + evaluate_weekly_report_events(db) + evaluate_reminder_events(db, now)
        notifications = process_pending_agent_events(db, now); db.commit()
        return {"events_created": created, "notifications_created": notifications}
    except Exception:
        db.rollback(); logger.exception("event_evaluation_failed"); raise


def list_notifications(db: Session, patient: int | None = None) -> list[Notification]:
    patient = patient or patient_id(db)
    return list(db.scalars(select(Notification).where(Notification.patient_id == patient).order_by(Notification.created_at.desc())).all())


def set_notification_status(db: Session, notification_id: int, status: str, patient: int | None = None) -> Notification:
    patient = patient or patient_id(db); notification = db.scalar(select(Notification).where(Notification.id == notification_id, Notification.patient_id == patient))
    if not notification: raise LookupError("Notification not found.")
    notification.status = status; db.commit(); db.refresh(notification); return notification


def create_reminder(db: Session, reminder_type: str, message: str, due_at: datetime, patient: int | None = None) -> Reminder:
    patient = patient or patient_id(db); reminder = Reminder(patient_id=patient, reminder_type=reminder_type, message=message, due_at=due_at)
    db.add(reminder); db.commit(); db.refresh(reminder); return reminder
