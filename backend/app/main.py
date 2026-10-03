import logging
from sqlalchemy import inspect, text
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.seed.demo import seed_demo_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")], allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["*"])
app.include_router(router)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    migrations = {"weekly_reports": {"structured_data": "JSON"}, "agent_events": {"event_key": "VARCHAR(255)"}, "notifications": {"category": "VARCHAR(60) DEFAULT 'general'", "event_id": "INTEGER"}}
    with engine.begin() as connection:
        for table, columns in migrations.items():
            existing = {column["name"] for column in inspect(engine).get_columns(table)}
            for name, definition in columns.items():
                if name not in existing: connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))
    if settings.demo_mode:
        with SessionLocal() as db:
            seed_demo_data(db)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "sugar-path"}
