from dataclasses import dataclass
import os
from pathlib import Path
from dotenv import load_dotenv


# The repository .env is for local development only and remains git-ignored.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _positive_int(name: str, default: str, *, minimum: int = 1, maximum: int | None = None) -> int:
    raw = os.getenv(name, default)
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc
    if value < minimum or (maximum is not None and value > maximum):
        bound = f" between {minimum} and {maximum}" if maximum is not None else f" at least {minimum}"
        raise ValueError(f"{name} must be{bound}.")
    return value


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Sugar Path")
    demo_mode: bool = os.getenv("DEMO_MODE", "true").lower() == "true"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./sugar_path.db")
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "")
    ollama_timeout_seconds: int = _positive_int("OLLAMA_TIMEOUT_SECONDS", "120")
    max_tool_iterations: int = _positive_int("MAX_TOOL_ITERATIONS", "10")
    medicine_missed_grace_minutes: int = _positive_int("MEDICINE_MISSED_GRACE_MINUTES", "60", minimum=0)
    medicine_morning_due_hour: int = _positive_int("MEDICINE_MORNING_DUE_HOUR", "8", minimum=0, maximum=23)
    medicine_evening_due_hour: int = _positive_int("MEDICINE_EVENING_DUE_HOUR", "20", minimum=0, maximum=23)
    glucose_low_threshold: int = _positive_int("GLUCOSE_LOW_THRESHOLD", "70", minimum=1)
    glucose_high_threshold: int = _positive_int("GLUCOSE_HIGH_THRESHOLD", "180", minimum=1)

    def __post_init__(self) -> None:
        if self.glucose_low_threshold >= self.glucose_high_threshold:
            raise ValueError("GLUCOSE_LOW_THRESHOLD must be lower than GLUCOSE_HIGH_THRESHOLD.")
        if self.medicine_morning_due_hour >= self.medicine_evening_due_hour:
            raise ValueError("MEDICINE_MORNING_DUE_HOUR must be earlier than MEDICINE_EVENING_DUE_HOUR.")


settings = Settings()
