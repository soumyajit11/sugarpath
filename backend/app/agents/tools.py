from datetime import datetime, timedelta
from math import ceil
from time import perf_counter
from typing import Any, Callable
import logging
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MedicationEvent, PatientProfile, User
from app.schemas.health import ConfirmMedicationIn
from app.services.cgm import demo_provider
from app.services.health import activities, confirm_medication, list_meals, log_meal, medications, patient_id, sleep
from app.schemas.memory import MemoryCreate
from app.services.memory import create_memory, retrieve_memories

logger = logging.getLogger(__name__)


class HoursArgs(BaseModel):
    hours: int = Field(default=24, ge=1, le=168)
class DaysArgs(BaseModel):
    days: int = Field(default=7, ge=1, le=31)
class EmptyArgs(BaseModel): pass
class MealArgs(BaseModel):
    description: str = Field(min_length=2, max_length=500)
    meal_type: str = Field(default="meal", pattern="^(breakfast|lunch|dinner|snack|meal)$")
class ConfirmArgs(BaseModel):
    medication_id: int = Field(gt=0)
    time_of_day: str | None = Field(default=None, pattern="^(morning|evening)$")
class MemoryReadArgs(BaseModel):
    query: str = Field(default="", max_length=500)
    memory_type: str | None = Field(default=None, pattern="^(routine|preference|patient_fact|system_observation)$")
class MemoryStoreArgs(MemoryCreate): pass


class Tool:
    def __init__(self, name: str, description: str, args: type[BaseModel], source: str, write: bool, handler: Callable[[Session, BaseModel], Any]):
        self.name, self.description, self.args, self.source, self.write, self.handler = name, description, args, source, write, handler
    def ollama_definition(self) -> dict:
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": self.args.model_json_schema()}}
    def execute(self, db: Session, arguments: dict) -> dict:
        started = perf_counter()
        try:
            parsed = self.args.model_validate(arguments)
            result = self.handler(db, parsed)
            logger.info("agent_tool_completed tool=%s latency_ms=%d", self.name, (perf_counter() - started) * 1000)
            return {"ok": True, "data": result.model_dump(mode="json") if hasattr(result, "model_dump") else result}
        except (ValidationError, ValueError, LookupError) as exc:
            logger.warning("agent_tool_rejected tool=%s error=%s", self.name, type(exc).__name__)
            return {"ok": False, "error": "The requested information could not be retrieved."}
        except Exception:
            logger.exception("agent_tool_failed tool=%s", self.name)
            return {"ok": False, "error": "The requested information is temporarily unavailable."}


def _history(db: Session, args: DaysArgs) -> dict:
    since = datetime.now() - timedelta(days=args.days)
    events = db.scalars(select(MedicationEvent).where(MedicationEvent.timestamp >= since).order_by(MedicationEvent.timestamp.desc())).all()
    return {"days": args.days, "taken": sum(event.status == "taken" for event in events), "missed": sum(event.status == "missed" for event in events), "events": [{"timestamp": event.timestamp, "status": event.status} for event in events]}

def _profile(db: Session, _: EmptyArgs) -> dict:
    profile = db.scalar(select(PatientProfile).limit(1))
    if not profile: raise LookupError()
    user = db.get(User, profile.user_id)
    return {"name": user.name, "age": profile.age, "condition": profile.condition, "typical_breakfast_time": profile.typical_breakfast_time, "typical_walk_minutes": profile.typical_walk_minutes}

def _raw_glucose(db: Session, args: HoursArgs):
    now = datetime.now()
    return demo_provider(db).readings(now - timedelta(hours=args.hours), now)

def _glucose(db: Session, args: HoursArgs) -> dict:
    readings = _raw_glucose(db, args)
    # The API retains every five-minute reading; the model receives a compact,
    # structured view so a local model can reason without context overload.
    stride = max(1, len(readings) // 24)
    representative = readings[::stride]
    if representative[-1].timestamp != readings[-1].timestamp:
        representative.append(readings[-1])
    values = [item.value_mg_dl for item in readings]
    high = max(readings, key=lambda item: item.value_mg_dl)
    low = min(readings, key=lambda item: item.value_mg_dl)
    return {
        "hours": args.hours,
        "reading_count": len(readings),
        "average_mg_dl": round(sum(values) / len(values)),
        "lowest": low.model_dump(mode="json"),
        "highest": high.model_dump(mode="json"),
        "representative_readings": [item.model_dump(mode="json") for item in representative],
    }
def _current_glucose(db: Session, _: EmptyArgs) -> dict:
    return _raw_glucose(db, HoursArgs(hours=1))[-1].model_dump(mode="json")
def _meals(db: Session, args: HoursArgs) -> list[dict]:
    return [item.model_dump(mode="json") for item in list_meals(db, ceil(args.hours / 24)) if item.timestamp >= datetime.now() - timedelta(hours=args.hours)]
def _meds(db: Session, _: EmptyArgs) -> list[dict]: return [item.model_dump(mode="json") for item in medications(db)]
def _activity(db: Session, args: DaysArgs) -> list[dict]: return [item.model_dump(mode="json") for item in activities(db, args.days)]
def _sleep(db: Session, args: DaysArgs) -> list[dict]: return [item.model_dump(mode="json") for item in sleep(db, args.days)]
def _daily(db: Session, _: EmptyArgs) -> dict:
    return {"current_glucose": _current_glucose(db, EmptyArgs()), "meals": _meals(db, HoursArgs(hours=24)), "medicine": _meds(db, EmptyArgs()), "activity": _activity(db, DaysArgs(days=1)), "sleep": _sleep(db, DaysArgs(days=1))}
def _log_meal(db: Session, args: MealArgs): return log_meal(db, args.description, args.meal_type)
def _meal_before_highest(db: Session, _: EmptyArgs) -> dict:
    now = datetime.now()
    readings = demo_provider(db).readings(now - timedelta(hours=24), now)
    highest = max(readings, key=lambda item: item.value_mg_dl)
    recent = list_meals(db, 1)
    before = [meal for meal in recent if meal.timestamp <= highest.timestamp]
    meal = max(before, key=lambda item: item.timestamp) if before else None
    return {
        "highest_glucose_mg_dl": highest.value_mg_dl,
        "highest_glucose_at": highest.timestamp,
        "meal_before_highest": meal.model_dump(mode="json") if meal else None,
    }
def _morning_glucose_context(db: Session, _: EmptyArgs) -> dict:
    """Structured multi-source context for a cautious morning-rise explanation."""
    now = datetime.now()
    readings = _raw_glucose(db, HoursArgs(hours=24))
    morning = [item for item in readings if 5 <= item.timestamp.hour < 12]
    breakfast_meals = [item for item in list_meals(db, 1) if item.meal_type == "breakfast"]
    medication = _history(db, DaysArgs(days=1))
    recent_sleep = _sleep(db, DaysArgs(days=2))
    recent_activity = _activity(db, DaysArgs(days=2))
    def glucose_stats(items):
        values = [item.value_mg_dl for item in items]
        high = max(items, key=lambda item: item.value_mg_dl)
        return {"average_mg_dl": round(sum(values) / len(values)), "highest_mg_dl": high.value_mg_dl, "highest_at": high.timestamp}
    return {
        "morning_glucose": glucose_stats(morning),
        "prior_24h_glucose": glucose_stats(readings),
        "breakfasts": [item.model_dump(mode="json") for item in breakfast_meals[:2]],
        "medicine_adherence": {"taken": medication["taken"], "missed": medication["missed"]},
        "latest_sleep": recent_sleep[0] if recent_sleep else None,
        "latest_activity": recent_activity[0] if recent_activity else None,
    }
def _confirm(db: Session, args: ConfirmArgs):
    time_of_day = args.time_of_day or ("morning" if datetime.now().hour < 15 else "evening")
    return confirm_medication(db, args.medication_id, time_of_day)
def _memories(db: Session, args: MemoryReadArgs):
    return [{"memory_type": item.memory_type, "content": item.content, "source": item.source, "updated_at": item.updated_at} for item in retrieve_memories(db, args.query, args.memory_type)]
def _store_memory(db: Session, args: MemoryStoreArgs):
    memory, created = create_memory(db, MemoryCreate(**args.model_dump()))
    return {"memory_type": memory.memory_type, "content": memory.content, "source": memory.source, "created": created}


REGISTRY = [
    Tool("get_current_glucose", "Get the latest synthetic glucose reading.", EmptyArgs, "Current glucose", False, _current_glucose),
    Tool("get_glucose_history", "Get synthetic glucose readings for a requested number of hours.", HoursArgs, "Glucose history", False, _glucose),
    Tool("get_recent_meals", "Get stored meals from the requested recent hours.", HoursArgs, "Meals", False, _meals),
    Tool("get_medication_schedule", "Get today's medication schedule and status.", EmptyArgs, "Medicine schedule", False, _meds),
    Tool("get_medication_history", "Get deterministic medication event totals and history.", DaysArgs, "Medicine history", False, _history),
    Tool("get_activity_history", "Get stored activity history.", DaysArgs, "Activity", False, _activity),
    Tool("get_sleep_history", "Get stored sleep history.", DaysArgs, "Sleep", False, _sleep),
    Tool("get_daily_summary", "Get a concise structured summary of today's stored data.", EmptyArgs, "Daily summary", False, _daily),
    Tool("get_patient_profile", "Get the fictional patient's stored profile.", EmptyArgs, "Patient profile", False, _profile),
    Tool("get_meal_before_highest_glucose", "Deterministically find the stored meal before the highest glucose reading in the last 24 hours.", EmptyArgs, "Glucose history and Meals", False, _meal_before_highest),
    Tool("get_morning_glucose_context", "Get glucose, meals, medicine, sleep, and activity context for a cautious explanation of a morning glucose rise.", EmptyArgs, "Glucose history, Meals, Medicine history, Sleep, and Activity", False, _morning_glucose_context),
    Tool("get_agent_memories", "Retrieve relevant, structured long-term memories only when the patient asks about preferences, routines, facts, or what Sugar Path remembers.", MemoryReadArgs, "What Sugar Path remembers", False, _memories),
    Tool("log_meal", "Log a meal using a local deterministic food dataset.", MealArgs, "Meals", True, _log_meal),
    Tool("confirm_medication", "Confirm that an already-prescribed medicine was taken.", ConfirmArgs, "Medicine history", True, _confirm),
    Tool("store_agent_memory", "Store an explicitly requested, non-medical long-term preference, routine, or patient fact. Never store a full conversation or treatment instruction.", MemoryStoreArgs, "What Sugar Path remembers", True, _store_memory),
]
TOOL_MAP = {tool.name: tool for tool in REGISTRY}
