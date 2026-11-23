from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

VALID = {
    "origin": "London",
    "destination": "Cairo",
    "start_date": "2027-03-14",
    "end_date": "2027-03-20",
    "travellers": 2,
    "interests": ["history", "food"],
}


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_create_trip_returns_id_and_defaults():
    body = client.post("/trips", json=VALID).json()
    assert body["id"]
    assert body["pace"] == "balanced"
    assert body["interests"] == ["history", "food"]


def test_create_trip_rejects_reversed_dates():
    resp = client.post("/trips", json={**VALID, "end_date": "2027-03-01"})
    assert resp.status_code == 422


def test_create_trip_rejects_zero_travellers():
    assert client.post("/trips", json={**VALID, "travellers": 0}).status_code == 422
