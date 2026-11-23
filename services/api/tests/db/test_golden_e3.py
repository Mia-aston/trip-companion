"""Golden slices E3 / E3b (docs/TESTING.md) through the API: partial regeneration changes only its day."""

from collections.abc import Iterator
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session
from app.domain.routing.geo import haversine_m
from app.domain.shared.models import GeoPoint
from app.main import app
from app.providers.mock_places import MockPlacesProvider

CAIRO_TZ = ZoneInfo("Africa/Cairo")


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
def egypt(client, egypt_trip_create):
    trip = client.post("/v1/trips", json=egypt_trip_create).json()
    base = f"/v1/trips/{trip['id']}/itinerary"
    v1 = client.post(f"{base}/generate").json()
    assert v1["version"] == 1
    return trip, base


def _days(plan) -> dict[str, list[dict]]:
    return {d["date"]: d["items"] for d in plan["days"]}


def _ok(resp, status=201):
    assert resp.status_code == status, resp.text
    return resp.json()


def test_e3_remove_aswan_and_stay_in_luxor_downtown(client, egypt):
    trip, base = egypt
    # v2: the user plans an Aswan day trip on 6 Nov (drops the planner's visits it overlaps)
    v2 = _ok(
        client.post(
            f"{base}/items", json={"date": "2026-11-06", "title": "Aswan day trip", "start": "08:00", "end": "19:00"}
        )
    )
    aswan = next(i for i in _days(v2)["2026-11-06"] if i["title"] == "Aswan day trip")
    assert v2["created_by"] == "user" and v2["diff"]["changed_dates"] == ["2026-11-06"]

    # v3: "Remove Aswan; stay around Luxor downtown"
    v3 = _ok(
        client.post(
            f"{base}/regenerate",
            json={
                "scope": {"date": "2026-11-06"},
                "remove_item_keys": [aswan["item_key"]],
                "stay_within_m": 3000,
                "pace": "relaxed",
                "note": "Remove Aswan; stay around Luxor downtown",
            },
        )
    )
    assert (v3["version"], v3["parent_version"], v3["reason"]) == (3, 2, "Remove Aswan; stay around Luxor downtown")
    assert not [w for w in v3["warnings"] if w["severity"] == "error"]

    before, after = _days(v2), _days(v3)
    # only 6 Nov changed; every other day is identical
    assert v3["diff"]["changed_dates"] == ["2026-11-06"]
    assert {d: items for d, items in after.items() if d != "2026-11-06"} == {
        d: items for d, items in before.items() if d != "2026-11-06"
    }
    # Aswan gone, replaced by Luxor visits within 3 km of the centre
    new_day = after["2026-11-06"]
    assert "Aswan day trip" not in [i["title"] for i in new_day]
    luxor = MockPlacesProvider().resolve_city("Luxor").location
    visits = [i for i in new_day if i["kind"] == "place"]
    assert visits
    for v in visits:
        place = MockPlacesProvider().details(v["place_id"])
        assert haversine_m(luxor, GeoPoint(lat=place.location.lat, lon=place.location.lon)) <= 3000
    # the departure flight is untouched and everything ends before the 19:30 airport cut-off
    flight = next(i for i in new_day if i["title"] == "Departure flight from Luxor")
    assert flight == next(i for i in before["2026-11-06"] if i["title"] == "Departure flight from Luxor")
    for i in new_day:
        if i["kind"] != "booking":
            assert datetime.fromisoformat(i["ends_at"]).astimezone(CAIRO_TZ).strftime("%H:%M") <= "19:30"

    # bookings everywhere unchanged
    def bookings(plan):
        return sorted(
            (i["item_key"], i["starts_at"], i["ends_at"])
            for d in plan["days"]
            for i in d["items"]
            if i["kind"] == "booking"
        )  # noqa: E731

    assert bookings(v3) == bookings(v2)
    # history is kept
    assert client.get(f"{base}?version=2").json() == v2


def test_e3b_balloon_cancelled_only_that_morning(client, egypt):
    trip, base = egypt
    v1 = client.get(base).json()
    day5 = _days(v1)["2026-11-05"]
    karnak = next(i for i in day5 if i["kind"] == "place")  # the first visit of the day gets locked
    v2 = _ok(client.post(f"{base}/items/{karnak['item_key']}/lock", json={"locked": True}), 200)

    balloon = next(b for b in trip["bookings"] if b["title"] == "Hot air balloon")
    assert client.delete(f"/v1/trips/{trip['id']}/bookings/{balloon['id']}").status_code == 204
    v3 = _ok(
        client.post(f"{base}/regenerate", json={"scope": {"date": "2026-11-05"}, "note": "Balloon cancelled (wind)"})
    )

    assert v3["diff"]["changed_dates"] == ["2026-11-05"]
    titles = [i["title"] for i in _days(v3)["2026-11-05"]]
    assert "Hot air balloon" not in titles
    assert [r["title"] for r in v3["diff"]["removed"] if r["kind"] == "booking"] == ["Hot air balloon"]
    kept = next(i for i in _days(v3)["2026-11-05"] if i["item_key"] == karnak["item_key"])
    assert kept == {**karnak, "locked": True}  # locked visit identical
    assert {d: i for d, i in _days(v3).items() if d != "2026-11-05"} == {
        d: i for d, i in _days(v2).items() if d != "2026-11-05"
    }
