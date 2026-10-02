import os
os.environ["DATABASE_URL"] = "sqlite:///./test_sugar_path.db"

from fastapi.testclient import TestClient
from app.main import app


def test_dashboard_serves_seeded_demo_patient():
    with TestClient(app) as client:
        response = client.get("/api/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert payload["patient_name"] == "Rahul Sen"
    assert payload["glucose"]["synthetic"] is True
    assert len(payload["medicines"]) == 2
    assert isinstance(payload["glucose"]["value_mg_dl"], int)
    assert payload["glucose"]["value_mg_dl"] > 0
