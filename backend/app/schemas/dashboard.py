from datetime import datetime
from pydantic import BaseModel


class GlucoseCard(BaseModel):
    value_mg_dl: int
    trend: str
    updated_at: datetime
    synthetic: bool


class MedicineCard(BaseModel):
    label: str
    detail: str
    status: str


class MealCard(BaseModel):
    description: str
    meal_type: str
    timestamp: datetime
    carbs_g: float


class ActivityCard(BaseModel):
    description: str
    duration_minutes: int
    steps: int | None = None


class DashboardResponse(BaseModel):
    patient_name: str
    greeting: str
    glucose: GlucoseCard
    medicines: list[MedicineCard]
    last_meal: MealCard
    activity: ActivityCard
    demo_mode: bool
