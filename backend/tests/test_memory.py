import pytest
from fastapi.testclient import TestClient

from app.agents.orchestrator import SugarPathAgent
from app.agents.tools import TOOL_MAP
from app.database import SessionLocal
from app.main import app
from app.services.memory import list_memories


def tool_call(name: str, arguments: dict) -> dict:
    return {"content": "", "tool_calls": [{"function": {"name": name, "arguments": arguments}}]}


class FakeClient:
    def __init__(self, replies): self.replies = replies
    def chat(self, messages, tools): return self.replies.pop(0)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_memory_api_create_retrieve_deduplicate_and_delete(client):
    payload = {"memory_type": "routine", "content": "Usually eats breakfast at 8 AM", "source": "user_explicit"}
    created = client.post("/api/memories", json=payload)
    assert created.status_code == 201
    memory_id = created.json()["id"]
    duplicate = client.post("/api/memories", json=payload)
    assert duplicate.status_code == 201 and duplicate.json()["id"] == memory_id
    listed = client.get("/api/memories")
    assert sum(item["id"] == memory_id for item in listed.json()) == 1
    assert client.delete(f"/api/memories/{memory_id}").status_code == 204
    assert memory_id not in [item["id"] for item in client.get("/api/memories").json()]


def test_memory_api_rejects_invalid_or_medical_memory(client):
    assert client.post("/api/memories", json={"memory_type": "unknown", "content": "Anything", "source": "user_explicit"}).status_code == 422
    assert client.post("/api/memories", json={"memory_type": "patient_fact", "content": "Take extra insulin when glucose is high", "source": "user_explicit"}).status_code == 422


def test_memory_tool_and_agent_read_write_path(client):
    db = SessionLocal()
    try:
        result = TOOL_MAP["store_agent_memory"].execute(db, {"memory_type": "preference", "content": "Prefers concise answers", "source": "user_explicit"})
        assert result["ok"] and result["data"]["content"] == "Prefers concise answers"
        read = TOOL_MAP["get_agent_memories"].execute(db, {"query": "concise answers"})
        assert read["ok"] and read["data"][0]["content"] == "Prefers concise answers"
        agent = SugarPathAgent(client=FakeClient([tool_call("get_agent_memories", {"query": "concise"}), {"content": "You prefer concise answers."}]))
        reply = agent.respond(db, "What preference do you remember about me?")
        assert reply["status"] == "ok" and "What Sugar Path remembers" in reply["sources_used"]
        writer = SugarPathAgent(client=FakeClient([tool_call("store_agent_memory", {"memory_type": "routine", "content": "Usually walks after dinner", "source": "user_explicit"}), {"content": "I will remember that."}]))
        assert writer.respond(db, "Remember that I usually walk after dinner.")["status"] == "ok"
        assert any("walks after dinner" in item.content for item in list_memories(db))
    finally:
        db.close()


def test_deleted_memory_is_not_returned_and_safety_wins(client):
    created = client.post("/api/memories", json={"memory_type": "routine", "content": "Usually eats breakfast at 8 AM", "source": "user_explicit"}).json()
    assert client.delete(f"/api/memories/{created['id']}").status_code == 204
    db = SessionLocal()
    try:
        assert TOOL_MAP["get_agent_memories"].execute(db, {"query": "breakfast"})["data"] == []
        response = SugarPathAgent(client=FakeClient([])).respond(db, "Remember that I should increase my insulin dose.")
        assert response["status"] == "safe_boundary"
    finally:
        db.close()
