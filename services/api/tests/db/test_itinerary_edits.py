"""ITIN-003 item edits through the API: each writes a validated new version."""

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


@pytest.fixture
def plan(client, egypt_trip_create):
    trip = client.post("/v1/trips", json=egypt_trip_create).json()
    base = f"/v1/trips/{trip['id']}/itinerary"
    return trip, base, client.post(f"{base}/generate").json()


def _item(plan, date, kind="place"):
    return next(i for d in plan["days"] if d["date"] == date for i in d["items"] if i["kind"] == kind)


def test_edits_need_a_plan(client, egypt_trip_create):
    trip = client.post("/v1/trips", json=egypt_trip_create).json()
    resp = client.post(
        f"/v1/trips/{trip['id']}/itinerary/items",
        json={"date": "2026-11-01", "title": "x", "start": "10:00", "end": "11:00"},
    )
    assert resp.status_code == 404


def test_move_item_and_diff(client, plan):
    _, base, v1 = plan
    item = _item(v1, "2026-11-05")
    v2 = client.patch(f"{base}/items/{item['item_key']}", json={"start": "15:00", "end": "16:30"}).json()
    assert v2["version"] == 2 and v2["created_by"] == "user" and v2["reason"].startswith("Edited")
    changed = v2["diff"]["changed"]
    assert any(c["item_key"] == item["item_key"] and "starts_at" in c["fields"] for c in changed)


def test_move_into_closed_hours_rejected(client, plan):
    _, base, v1 = plan
    museum = next(i for d in v1["days"] for i in d["items"] if i.get("place_id") == "mock:luxor-museum")
    resp = client.patch(f"{base}/items/{museum['item_key']}", json={"start": "14:00", "end": "15:30"})  # closed 14-17
    assert resp.status_code == 422
    assert any(v["rule"] == "V4" for v in resp.json()["error"]["details"])
    assert client.get(base).json()["version"] == 1  # nothing stored


def test_bookings_cannot_be_edited_or_deleted(client, plan):
    _, base, v1 = plan
    booking = _item(v1, "2026-11-04", kind="booking")
    assert client.patch(f"{base}/items/{booking['item_key']}", json={"start": "09:00"}).status_code == 409
    assert client.delete(f"{base}/items/{booking['item_key']}").status_code == 409
    assert client.post(f"{base}/items/{booking['item_key']}/lock", json={"locked": False}).status_code == 409


def test_locked_item_must_be_unlocked_first(client, plan):
    _, base, v1 = plan
    item = _item(v1, "2026-11-01")
    client.post(f"{base}/items/{item['item_key']}/lock", json={"locked": True})
    assert client.delete(f"{base}/items/{item['item_key']}").status_code == 409
    client.post(f"{base}/items/{item['item_key']}/lock", json={"locked": False})
    v = client.delete(f"{base}/items/{item['item_key']}").json()
    assert item["item_key"] not in [i["item_key"] for d in v["days"] for i in d["items"]]
    assert v["version"] == 4


def test_added_item_replaces_overlapping_planner_items_and_survives_generate(client, plan):
    _, base, v1 = plan
    v2 = client.post(
        f"{base}/items", json={"date": "2026-11-02", "title": "Meet friends", "start": "09:00", "end": "12:00"}
    ).json()
    day = next(d for d in v2["days"] if d["date"] == "2026-11-02")["items"]
    mine = next(i for i in day if i["title"] == "Meet friends")
    assert mine["source"] == "user" and mine["kind"] == "custom"
    assert all(
        not (i["starts_at"] < mine["ends_at"] and mine["starts_at"] < i["ends_at"]) for i in day if i is not mine
    )
    v3 = client.post(f"{base}/generate").json()
    assert mine["item_key"] in [i["item_key"] for d in v3["days"] for i in d["items"]]


def test_add_item_on_day_without_time_rejected(client, plan):
    _, base, _ = plan
    resp = client.post(f"{base}/items", json={"date": "2026-10-31", "title": "Walk", "start": "20:00", "end": "21:00"})
    assert resp.status_code == 422 and any(v["rule"] == "V1" for v in resp.json()["error"]["details"])


def test_regenerate_validation(client, plan):
    _, base, _ = plan
    assert client.post(f"{base}/regenerate", json={"scope": {"date": "2027-01-01"}}).status_code == 422
    unknown = "00000000-0000-0000-0000-000000000001"
    assert (
        client.post(
            f"{base}/regenerate", json={"scope": {"date": "2026-11-06"}, "remove_item_keys": [unknown]}
        ).status_code
        == 404
    )
    assert (
        client.post(f"{base}/regenerate", json={"scope": {"date": "2026-11-06"}, "stay_within_m": 10}).status_code
        == 422
    )


def test_unknown_item(client, plan):
    _, base, _ = plan
    assert client.delete(f"{base}/items/00000000-0000-0000-0000-000000000009").status_code == 404
