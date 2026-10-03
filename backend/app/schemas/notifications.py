from datetime import datetime
from typing import Literal
from pydantic import BaseModel

NotificationStatus = Literal["unread", "read", "dismissed"]


class NotificationOut(BaseModel):
    id: int; message: str; category: str; status: NotificationStatus; created_at: datetime; event_id: int | None = None
    model_config = {"from_attributes": True}


class EventEvaluationOut(BaseModel):
    events_created: int; notifications_created: int


class ReminderCreate(BaseModel):
    reminder_type: Literal["medicine", "activity", "meal_logging", "custom"]
    message: str
    due_at: datetime


class ReminderOut(BaseModel):
    id: int; reminder_type: str; message: str; due_at: datetime; status: str
    model_config = {"from_attributes": True}
