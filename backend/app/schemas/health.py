from datetime import datetime
from pydantic import BaseModel, Field


class GlucoseReadingOut(BaseModel):
    timestamp: datetime
    value_mg_dl: int
    trend: str | None
    source: str
    synthetic: bool


class MedicationOut(BaseModel):
    id: int
    name: str
    dose: str
    time_of_day: str
    instructions: str
    status: str
    event_time: datetime | None = None


class ConfirmMedicationIn(BaseModel):
    time_of_day: str = Field(pattern="^(morning|evening)$")


class MealCreate(BaseModel):
    description: str = Field(min_length=2, max_length=500)
    meal_type: str = Field(default="meal", pattern="^(breakfast|lunch|dinner|snack|meal)$")


class MealOut(BaseModel):
    id: int
    timestamp: datetime
    meal_type: str
    description: str
    estimated_carbs_g: float
    calories: float | None
    protein_g: float | None
    fat_g: float | None
    items: list[str]
    source: str


class ActivityOut(BaseModel):
    timestamp: datetime
    activity_type: str
    duration_minutes: int
    steps: int | None


class SleepOut(BaseModel):
    start_time: datetime
    end_time: datetime
    quality: str | None
    duration_minutes: int
