"""FLIGHT-002: trip flight search through the API, with snapshots."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.models import TransportOptionRow
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


@pytest.fixture
def trip(client, egypt_trip_create) -> dict:
    return client.post("/v1/trips", json=egypt_trip_create).json()


OUT = {"direction": "outbound", "from_airport": "LON", "to_airport": "CAI"}


def _keys(body):
    return [o["offer_id"].split("-")[0] for o in body["offers"]]


def test_search_uses_trip_passengers_and_prefs(client, trip):
    resp = client.post(f"/v1/trips/{trip['id']}/flights/search", json=OUT)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    s = body["search"]
    assert (s["date"], s["adults"], s["cabin"], s["max_stops"], s["checked_bags"]) == ("2026-10-31", 2, "economy", 1, 1)
    # trip prefs need 1 checked bag → the no-bag 1-stop fare is filtered; business filtered by cabin
    assert _keys(body) == ["nm778", "nm780"]
    assert body["filtered_out"] == 2
    assert [o["total"] for o in body["offers"]] == [
        {"amount": "580.00", "currency": "GBP"},
        {"amount": "680.00", "currency": "GBP"},
    ]
    first = body["offers"][0]
    assert first["stops"] == 0 and first["duration_minutes"] == 300 and first["expires_at"] > body["searched_at"]


def test_request_overrides_prefs_and_sort(client, trip):
    body = client.post(f"/v1/trips/{trip['id']}/flights/search", json={**OUT, "checked_bags": 0}).json()
    assert _keys(body)[0] == "bm1980"  # cheapest once bags are not required
    fastest = client.post(
        f"/v1/trips/{trip['id']}/flights/search", json={**OUT, "checked_bags": 0, "sort": "duration"}
    ).json()
    assert _keys(fastest)[-1] == "bm1980"
    business = client.post(f"/v1/trips/{trip['id']}/flights/search", json={**OUT, "cabin": "business"}).json()
    assert _keys(business) == ["nm780j"]


def test_return_defaults_to_trip_end(client, trip):
    body = client.post(
        f"/v1/trips/{trip['id']}/flights/search",
        json={"direction": "return", "from_airport": "LXR", "to_airport": "LON"},
    ).json()
    assert body["search"]["date"] == "2026-11-06"
    assert "nm315" in _keys(body)


def test_snapshots_stored_per_search(client, trip, session):
    a = client.post(f"/v1/trips/{trip['id']}/flights/search", json=OUT).json()
    b = client.post(f"/v1/trips/{trip['id']}/flights/search", json=OUT).json()
    assert a["search_id"] != b["search_id"]
    rows = session.scalars(select(TransportOptionRow).where(TransportOptionRow.trip_id == trip["id"])).all()
    assert len(rows) == 4 and {r.direction for r in rows} == {"outbound"}
    assert all(r.expires_at > r.fetched_at and r.selected_at is None for r in rows)
    assert all("stops" not in r.offer for r in rows)  # normalized offer only, computed fields rebuilt on read


def test_unknown_route_is_empty(client, trip):
    body = client.post(f"/v1/trips/{trip['id']}/flights/search", json={**OUT, "to_airport": "SYD"}).json()
    assert body["offers"] == [] and body["filtered_out"] == 0


@pytest.mark.parametrize("bad", [{"from_airport": "cai"}, {"to_airport": "LON"}, {"direction": "up"}, {"max_stops": 9}])
def test_invalid_search(client, trip, bad):
    resp = client.post(f"/v1/trips/{trip['id']}/flights/search", json={**OUT, **bad})
    assert resp.status_code == 422


def test_unknown_trip(client, session):
    resp = client.post("/v1/trips/00000000-0000-0000-0000-000000000000/flights/search", json=OUT)
    assert resp.status_code == 404
    assert session.scalar(select(func.count()).select_from(TransportOptionRow)) == 0
