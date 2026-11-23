"""PLACE-003: /v1/places and /v1/trips/{id}/day-candidates (golden slice E2 at API level)."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session
from app.main import app


@pytest.fixture
def client(session) -> Iterator[TestClient]:
    def _session():
        yield session

    app.dependency_overrides[get_session] = _session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


LUXOR = {"lat": 25.6872, "lon": 32.6396}


def test_search_places(client):
    resp = client.post("/v1/places/search", json={"query": "temple", "near": LUXOR, "radius_m": 10_000})
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert names[0] == "Luxor Temple" and "Karnak Temple" in names
    assert all(p["provenance"]["source"] == "provider" for p in resp.json())


def test_search_category_and_limit(client):
    body = client.post(
        "/v1/places/search", json={"near": LUXOR, "radius_m": 20_000, "categories": ["museum"], "limit": 1}
    ).json()
    assert len(body) == 1 and "museum" in body[0]["categories"]


def test_search_validation(client):
    resp = client.post("/v1/places/search", json={"near": {"lat": 99, "lon": 0}})
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "validation_error"


def test_get_place_and_404(client):
    place = client.get("/v1/places/mock:karnak").json()
    assert place["id"] == "mock:karnak" and place["opening_hours"]
    resp = client.get("/v1/places/mock:nope")
    assert resp.status_code == 404 and resp.json()["error"]["code"] == "not_found"


def test_day_candidates_for_egypt_trip(client, egypt_trip_create):
    trip = client.post("/v1/trips", json=egypt_trip_create).json()
    resp = client.get(f"/v1/trips/{trip['id']}/day-candidates")
    assert resp.status_code == 200, resp.text
    days = {d["date"]: d for d in resp.json()["days"]}
    assert days["2026-10-31"]["capacity_minutes"] == 0
    assert days["2026-11-06"]["window"]["end"] == "19:30:00"
    assert days["2026-11-01"]["candidates"][0]["name"] == "Giza Pyramids"
    assert resp.json()["unmet_must_dos"] == []
    # second call is served from the cache and is identical
    assert client.get(f"/v1/trips/{trip['id']}/day-candidates").json() == resp.json()


def test_day_candidates_unknown_trip(client):
    resp = client.get("/v1/trips/00000000-0000-0000-0000-000000000000/day-candidates")
    assert resp.status_code == 404
