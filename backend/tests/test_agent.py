import pytest
from fastapi.testclient import TestClient

from app.agents.orchestrator import SugarPathAgent
from app.agents.tools import TOOL_MAP
from app.database import SessionLocal
from app.main import app
from app.services.ollama_service import OllamaUnavailable


def tool_call(name: str, arguments: dict) -> dict:
    return {"content": "", "tool_calls": [{"function": {"name": name, "arguments": arguments}}]}


class FakeClient:
    def __init__(self, replies: list[dict]): self.replies = replies
    def chat(self, messages, tools): return self.replies.pop(0)


class OfflineClient:
    def chat(self, messages, tools): raise OllamaUnavailable()


@pytest.fixture
def db():
    with TestClient(app):
        session = SessionLocal()
        try: yield session
        finally: session.close()


def test_registry_read_tool_and_invalid_tool_are_safe(db):
    result = TOOL_MAP["get_current_glucose"].execute(db, {})
    assert result["ok"] is True
    assert result["data"]["synthetic"] is True
    invalid = TOOL_MAP["get_glucose_history"].execute(db, {"hours": "not-a-number"})
    assert invalid["ok"] is False


def test_agent_executes_medication_tool_and_returns_sources(db):
    client = FakeClient([tool_call("get_medication_history", {"days": 7}), {"content": "Your stored medicine history is ready."}])
    response = SugarPathAgent(client=client).respond(db, "Did I take my morning medicine?")
    assert response["status"] == "ok"
    assert response["sources_used"] == ["Medicine history"]


def test_unknown_tool_and_validated_write_tool_are_contained(db):
    client = FakeClient([tool_call("not_a_real_tool", {}), {"content": "I could not complete that request."}])
    response = SugarPathAgent(client=client).respond(db, "Check something")
    assert response["status"] == "ok"
    written = TOOL_MAP["log_meal"].execute(db, {"description": "roti and dal", "meal_type": "lunch"})
    assert written["ok"] is True


@pytest.mark.parametrize("tool_name,args,source", [
    ("get_glucose_history", {"hours": 24}, "Glucose history"),
    ("get_recent_meals", {"hours": 24}, "Meals"),
    ("get_activity_history", {"days": 2}, "Activity"),
    ("get_sleep_history", {"days": 2}, "Sleep"),
])
def test_agent_core_read_tools(db, tool_name, args, source):
    client = FakeClient([tool_call(tool_name, args), {"content": "Here is your stored information."}])
    response = SugarPathAgent(client=client).respond(db, "Please check my information")
    assert response["status"] == "ok"
    assert source in response["sources_used"]


def test_unavailable_and_iteration_limit_are_graceful(db):
    unavailable = SugarPathAgent(client=OfflineClient()).respond(db, "How was my glucose?")
    assert unavailable["status"] == "unavailable"
    looping = SugarPathAgent(client=FakeClient([tool_call("get_current_glucose", {})] * 3), max_iterations=2).respond(db, "Check glucose")
    assert looping["status"] == "limit_reached"


def test_dose_change_is_deterministically_blocked(db):
    response = SugarPathAgent(client=OfflineClient()).respond(db, "Should I increase my Metformin?")
    assert response["status"] == "safe_boundary"
