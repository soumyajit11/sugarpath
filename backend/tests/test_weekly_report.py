from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from app.agents.orchestrator import SugarPathAgent
from app.agents.tools import TOOL_MAP
from app.database import SessionLocal
from app.main import app
from app.services.weekly_report import build_weekly_summary, current_week_start, generate_weekly_report


def tool_call(name: str, arguments: dict) -> dict:
    return {"content": "", "tool_calls": [{"function": {"name": name, "arguments": arguments}}]}


class FakeClient:
    def __init__(self, replies): self.replies = replies
    def chat(self, messages, tools): return self.replies.pop(0)


@pytest.fixture
def db():
    with TestClient(app):
        session = SessionLocal()
        try: yield session
        finally: session.close()


def test_weekly_summary_is_seven_days_and_calculates_sections(db):
    summary = build_weekly_summary(db)
    assert summary.week_end - summary.week_start == timedelta(days=6)
    assert summary.glucose.reading_count > 0
    assert summary.glucose.minimum_mg_dl <= summary.glucose.maximum_mg_dl
    assert summary.glucose.highest_at and summary.glucose.lowest_at
    assert summary.medicine.scheduled_doses == 14
    assert summary.medicine.taken_doses <= summary.medicine.scheduled_doses
    assert summary.medicine.adherence_percent is None or summary.medicine.adherence_percent <= 100
    assert summary.meals.logged_meals > 0
    assert summary.activity.total_minutes > 0 and summary.activity.active_days > 0
    assert summary.sleep.nights_recorded > 0


def test_weekly_report_persists_and_refreshes_without_duplicates(db):
    first = generate_weekly_report(db)
    second = generate_weekly_report(db)
    assert first.id == second.id
    assert second.summary.week_start == current_week_start()
    assert "Demo data only" in second.narrative


def test_weekly_api_tool_and_agent_path(db):
    with TestClient(app) as client:
        created = client.post("/api/reports/weekly/generate", json={})
        assert created.status_code == 200
        report = created.json(); assert report["summary"]["glucose"]["reading_count"] > 0
        assert client.get("/api/reports/weekly/current").json()["id"] == report["id"]
        assert client.get(f"/api/reports/weekly/{report['id']}").status_code == 200
    result = TOOL_MAP["get_weekly_summary"].execute(db, {})
    assert result["ok"] and "glucose" in result["data"]
    agent = SugarPathAgent(client=FakeClient([tool_call("get_weekly_summary", {}), {"content": "Here is your weekly summary."}]))
    reply = agent.respond(db, "How was my week?")
    assert reply["status"] == "ok" and "Weekly summary" in reply["sources_used"]


def test_weekly_summary_has_no_unsupported_pattern_when_evidence_is_weak(db):
    summary = build_weekly_summary(db, datetime.now().date() + timedelta(days=30))
    assert summary.patterns == []
    assert summary.glucose.reading_count == 0


def test_weekly_safety_boundary_still_wins(db):
    response = SugarPathAgent(client=FakeClient([])).respond(db, "How was my week and should I increase my Metformin?")
    assert response["status"] == "safe_boundary"
