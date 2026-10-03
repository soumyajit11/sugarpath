from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Timestamped, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True)


class PatientProfile(Timestamped, Base):
    __tablename__ = "patient_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    age: Mapped[int] = mapped_column(Integer)
    condition: Mapped[str] = mapped_column(String(120))
    typical_breakfast_time: Mapped[str] = mapped_column(String(10))
    typical_dinner_time: Mapped[str] = mapped_column(String(10))
    typical_walk_minutes: Mapped[int] = mapped_column(Integer)


class Medication(Timestamped, Base):
    __tablename__ = "medications"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"))
    name: Mapped[str] = mapped_column(String(120))
    dose: Mapped[str] = mapped_column(String(80))


class MedicationSchedule(Timestamped, Base):
    __tablename__ = "medication_schedules"
    id: Mapped[int] = mapped_column(primary_key=True)
    medication_id: Mapped[int] = mapped_column(ForeignKey("medications.id"))
    time_of_day: Mapped[str] = mapped_column(String(20))
    instructions: Mapped[str] = mapped_column(String(160))


class MedicationEvent(Timestamped, Base):
    __tablename__ = "medication_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    medication_id: Mapped[int] = mapped_column(ForeignKey("medications.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20))  # scheduled, taken, missed, skipped


class GlucoseReading(Timestamped, Base):
    __tablename__ = "glucose_readings"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    value_mg_dl: Mapped[int] = mapped_column(Integer)
    trend: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source: Mapped[str] = mapped_column(String(60), default="mock_cgm")
    synthetic: Mapped[bool] = mapped_column(Boolean, default=True)


class Meal(Timestamped, Base):
    __tablename__ = "meals"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    meal_type: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(Text)
    estimated_carbs_g: Mapped[float] = mapped_column(Float)
    calories: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(60), default="synthetic_seed")


class MealItem(Timestamped, Base):
    __tablename__ = "meal_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    meal_id: Mapped[int] = mapped_column(ForeignKey("meals.id"))
    name: Mapped[str] = mapped_column(String(120))
    quantity: Mapped[str] = mapped_column(String(80))


class ActivityEvent(Timestamped, Base):
    __tablename__ = "activity_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    activity_type: Mapped[str] = mapped_column(String(60))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    steps: Mapped[int | None] = mapped_column(Integer, nullable=True)


class SleepEvent(Timestamped, Base):
    __tablename__ = "sleep_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"))
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    quality: Mapped[str | None] = mapped_column(String(30), nullable=True)


class AgentMemory(Timestamped, Base):
    __tablename__ = "agent_memories"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"))
    memory_type: Mapped[str] = mapped_column(String(60))
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(60))


class Notification(Timestamped, Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="unread")
    category: Mapped[str] = mapped_column(String(60), default="general")
    event_id: Mapped[int | None] = mapped_column(ForeignKey("agent_events.id"), nullable=True, unique=True)


class AgentEvent(Timestamped, Base):
    __tablename__ = "agent_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"))
    event_type: Mapped[str] = mapped_column(String(60))
    event_key: Mapped[str] = mapped_column(String(255), unique=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Reminder(Timestamped, Base):
    __tablename__ = "reminders"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"))
    reminder_type: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(String(240))
    due_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(30), default="active")


class WeeklyReport(Timestamped, Base):
    __tablename__ = "weekly_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"))
    week_start: Mapped[datetime] = mapped_column(DateTime)
    content: Mapped[str] = mapped_column(Text)
    structured_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
