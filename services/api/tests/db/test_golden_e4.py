"""Golden slice E4 (docs/TESTING.md): a selected flight becomes the trip's time constraint."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update

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


def _search(client, trip, **extra):
    body = {"direction": "outbound", "from_airport": "LON", "to_airport": "CAI", **extra}
    return {
        o["offer_id"].split("-")[0]: o
        for o in client.post(f"/v1/trips/{trip['id']}/flights/search", json=body).json()["offers"]
    }


def _select(client, trip, offer):
    return client.post(f"/v1/trips/{trip['id']}/transport/select", json={"offer_id": offer["id"]})


def _day(client, trip, date):
    days = client.get(f"/v1/trips/{trip['id']}/day-candidates").json()["days"]
    return next(d for d in days if d["date"] == date)


def _flights(client, trip):
    return sorted(
        (b for b in client.get(f"/v1/trips/{trip['id']}").json()["bookings"] if b["kind"] == "flight"),
        key=lambda b: b["starts_at"],
    )


def test_e4_late_then_early_arrival(client, trip):
    offers = _search(client, trip)
    original_arrival = _flights(client, trip)[0]

    # late arrival 23:30 → 31 Oct has no sightseeing
    late = _select(client, trip, offers["nm778"])
    assert late.status_code == 200, late.text
    body = late.json()
    assert body["direction"] == "outbound" and body["replaced_booking_id"] == original_arrival["id"]
    assert body["booking"]["status"] == "tentative" and body["booking"]["cost"] == {
        "amount": "580.00",
        "currency": "GBP",
    }
    assert body["affected_dates"] == []  # same landing time as the booking it replaced
    assert _day(client, trip, "2026-10-31")["capacity_minutes"] == 0

    # early arrival 14:00 → 31 Oct opens up from 15:30 (+90 min)
    early = _select(client, trip, offers["nm780"]).json()
    assert early["affected_dates"] == ["2026-10-31"]
    day = _day(client, trip, "2026-10-31")
    assert day["window"]["start"] == "15:30:00" and day["capacity_minutes"] > 0 and day["candidates"]

    flights = _flights(client, trip)
    assert len(flights) == 2  # still one arrival + one departure
    assert flights[0]["reference"].startswith("nm780") and flights[1]["title"] == "Departure flight from Luxor"


def test_return_flight_replaces_departure(client, trip):
    back = {
        o["offer_id"].split("-")[0]: o
        for o in client.post(
            f"/v1/trips/{trip['id']}/flights/search",
            json={"direction": "return", "from_airport": "LXR", "to_airport": "LON"},
        ).json()["offers"]
    }
    resp = _select(client, trip, back["nm152"])  # LXR 15:10 → leave for the airport by 12:10
    assert resp.status_code == 200, resp.text
    assert resp.json()["affected_dates"] == ["2026-11-06"]
    assert _day(client, trip, "2026-11-06")["window"]["end"] == "12:10:00"
    assert _flights(client, trip)[0]["title"] == "Arrival flight to Cairo"  # outbound untouched


def test_expired_offer_conflict_changes_nothing(client, trip, session):
    offers = _search(client, trip)
    session.execute(
        update(TransportOptionRow).values(
            expires_at=datetime.now(UTC) - timedelta(minutes=1), fetched_at=datetime.now(UTC) - timedelta(minutes=31)
        )
    )
    before = client.get(f"/v1/trips/{trip['id']}").json()
    resp = _select(client, trip, offers["nm780"])
    assert resp.status_code == 409 and resp.json()["error"]["message"] == "Offer expired — search again"
    assert client.get(f"/v1/trips/{trip['id']}").json() == before


def test_unknown_offer_404(client, trip):
    assert _select(client, trip, {"id": "mock:nope"}).status_code == 404


def test_offer_from_another_trip_404(client, trip, egypt_trip_create):
    other = client.post("/v1/trips", json=egypt_trip_create).json()
    offers = _search(client, other)
    assert _select(client, trip, offers["nm780"]).status_code == 404


def test_flight_outside_trip_dates_rejected(client, trip):
    offers = _search(client, trip, date="2026-12-01")
    resp = _select(client, trip, offers["nm780"])
    assert resp.status_code == 422 and "outside the trip" in resp.json()["error"]["details"][0]
