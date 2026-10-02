from fastapi.testclient import TestClient
from app.main import app


def test_mock_cgm_returns_five_minute_history():
    with TestClient(app) as client:
        response = client.get("/api/glucose/history?hours=1")
    assert response.status_code == 200
    assert len(response.json()) >= 12
    assert all(item["synthetic"] for item in response.json())


def test_confirm_medicine_and_log_known_food():
    with TestClient(app) as client:
        medicine = client.get("/api/medicines").json()[0]
        confirmed = client.post(f"/api/medicines/{medicine['id']}/confirm", json={"time_of_day": "morning"})
        meal = client.post("/api/meals", json={"description": "I ate 2 rotis, dal and an egg.", "meal_type": "lunch"})
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "taken"
    assert meal.status_code == 201
    assert meal.json()["estimated_carbs_g"] > 0
