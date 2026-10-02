from dataclasses import dataclass
import os
from pathlib import Path
from dotenv import load_dotenv


# The repository .env is for local development only and remains git-ignored.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Sugar Path")
    demo_mode: bool = os.getenv("DEMO_MODE", "true").lower() == "true"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./sugar_path.db")
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "")
    ollama_timeout_seconds: int = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
    max_tool_iterations: int = int(os.getenv("MAX_TOOL_ITERATIONS", "10"))


settings = Settings()
