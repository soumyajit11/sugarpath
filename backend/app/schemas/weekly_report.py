from datetime import date, datetime
from pydantic import BaseModel


class GlucoseWeekly(BaseModel):
    reading_count: int; average_mg_dl: int | None; minimum_mg_dl: int | None; maximum_mg_dl: int | None
    highest_at: datetime | None; lowest_at: datetime | None; daily_averages: dict[str, int]; morning_average_mg_dl: int | None
    excursions_high: int; excursions_low: int


class MedicineWeekly(BaseModel):
    scheduled_doses: int; taken_doses: int; missed_doses: int; skipped_doses: int; adherence_percent: float | None
    morning: dict[str, int]; evening: dict[str, int]


class MealsWeekly(BaseModel):
    logged_meals: int; average_carbs_g: float | None; late_meals: int; recurring_meals: list[str]; highest_carb_meals: list[dict]


class ActivityWeekly(BaseModel):
    total_minutes: int; average_minutes_per_day: float; total_steps: int; average_steps_per_day: int; active_days: int


class SleepWeekly(BaseModel):
    nights_recorded: int; average_duration_minutes: int | None; shortest_minutes: int | None; longest_minutes: int | None; quality_counts: dict[str, int]


class ObservedPattern(BaseModel):
    description: str; matching_days: int; observed_days: int


class WeeklySummary(BaseModel):
    week_start: date; week_end: date; glucose: GlucoseWeekly; medicine: MedicineWeekly; meals: MealsWeekly
    activity: ActivityWeekly; sleep: SleepWeekly; patterns: list[ObservedPattern]; questions_for_clinician: list[str]
    relevant_preferences: list[str] = []; demo_data: bool = True


class WeeklyReportOut(BaseModel):
    id: int; patient_id: int; week_start: date; generated_at: datetime; summary: WeeklySummary; narrative: str


class WeeklyReportRequest(BaseModel):
    week_start: date | None = None
