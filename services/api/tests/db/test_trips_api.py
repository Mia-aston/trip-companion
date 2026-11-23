"""CORE-003: /v1/trips against PostGIS (golden slice E1 at API level)."""

from collections.abc import Iterator
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.models import ExpenseRow
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
def egypt(client, egypt_trip_create) -> dict:
    resp = client.post("/v1/trips", json=egypt_trip_create)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _error(resp, status: int, code: str) -> dict:
    assert resp.status_code == status, resp.text
    body = resp.json()["error"]
    assert body["code"] == code
    return body


# --- trip ------------------------------------------------------------------


def test_e1_create_then_get_is_identical(client, egypt):
    assert client.get(f"/v1/trips/{egypt['id']}").json() == egypt
    assert egypt["travellers"] == 2 and len(egypt["bookings"]) == 6
    assert egypt["bookings"][-1]["starts_at"] == "2026-11-06T20:30:00Z"  # 22:30 Cairo, UTC on the wire (A-11)


def test_get_unknown_trip_404(client):
    _error(client.get(f"/v1/trips/{uuid4()}"), 404, "not_found")


def test_patch_scalar_fields(client, egypt):
    resp = client.patch(f"/v1/trips/{egypt['id']}", json={"pace": "relaxed", "budget": None, "dietary": ["halal"]})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert (body["pace"], body["budget"], body["dietary"]) == ("relaxed", None, ["halal"])
    assert client.get(f"/v1/trips/{egypt['id']}").json() == body
    assert body["stops"] == egypt["stops"]  # untouched


def test_patch_shift_dates_moves_stops_and_keeps_ids(client, egypt):
    body = client.patch(f"/v1/trips/{egypt['id']}", json={"start_date": "2026-11-01", "end_date": "2026-11-07"}).json()
    assert [s["id"] for s in body["stops"]] == [s["id"] for s in egypt["stops"]]
    assert [(s["arrive_on"], s["leave_on"]) for s in body["stops"]] == [
        ("2026-11-01", "2026-11-04"),
        ("2026-11-04", "2026-11-05"),
        ("2026-11-05", "2026-11-07"),
    ]


def test_patch_length_without_stops_rejected(client, egypt):
    body = _error(client.patch(f"/v1/trips/{egypt['id']}", json={"end_date": "2026-11-07"}), 422, "validation_error")
    assert "stop nights must sum" in body["details"][0]
    assert client.get(f"/v1/trips/{egypt['id']}").json() == egypt  # nothing persisted


def test_patch_length_with_new_stops(client, egypt):
    stops = [{"city": "Cairo", "nights": 3}, {"city": "Western Desert", "nights": 1}, {"city": "Luxor", "nights": 3}]
    body = client.patch(f"/v1/trips/{egypt['id']}", json={"end_date": "2026-11-07", "stops": stops}).json()
    assert [s["nights"] for s in body["stops"]] == [3, 1, 3]
    assert body["stops"][-1]["leave_on"] == "2026-11-07"
    assert client.get(f"/v1/trips/{egypt['id']}").json()["stops"] == body["stops"]


def test_patch_cannot_drop_stop_used_by_booking(client, egypt):
    body = _error(
        client.patch(f"/v1/trips/{egypt['id']}", json={"stops": [{"city": "Cairo", "nights": 6}]}),
        422,
        "validation_error",
    )
    assert "Desert camp" in body["details"][0]


def test_patch_party_rules_rechecked_on_merged_trip(client, egypt):
    _error(client.patch(f"/v1/trips/{egypt['id']}", json={"adults": 1, "infants": 2}), 422, "validation_error")
    _error(client.patch(f"/v1/trips/{egypt['id']}", json={"title": None}), 422, "validation_error")


def test_patch_base_currency_carries_implied_settlement(client, egypt):
    body = client.patch(f"/v1/trips/{egypt['id']}", json={"base_currency": "EUR"}).json()
    assert body["settlement_currency"] == "EUR"


def test_delete_trip(client, egypt):
    assert client.delete(f"/v1/trips/{egypt['id']}").status_code == 204
    _error(client.get(f"/v1/trips/{egypt['id']}"), 404, "not_found")
    _error(client.delete(f"/v1/trips/{egypt['id']}"), 404, "not_found")


# --- members ---------------------------------------------------------------


def test_add_and_remove_member(client, egypt):
    resp = client.post(f"/v1/trips/{egypt['id']}/members", json={"display_name": "Linh", "role": "owner"})
    assert resp.status_code == 201
    member = resp.json()
    names = [m["display_name"] for m in client.get(f"/v1/trips/{egypt['id']}").json()["members"]]
    assert names == ["Mia", "QA", "Linh"]  # insertion order kept
    assert client.delete(f"/v1/trips/{egypt['id']}/members/{member['id']}").status_code == 204
    _error(client.delete(f"/v1/trips/{egypt['id']}/members/{member['id']}"), 404, "not_found")


def test_duplicate_member_conflict(client, egypt):
    _error(client.post(f"/v1/trips/{egypt['id']}/members", json={"display_name": "mia"}), 409, "conflict")


def test_member_with_expense_cannot_be_removed(client, egypt, session):
    payer = egypt["members"][0]["id"]
    session.add(
        ExpenseRow(trip_id=egypt["id"], description="Taxi", amount=Decimal("5"), currency="EGP", payer_id=payer)
    )
    session.flush()
    _error(client.delete(f"/v1/trips/{egypt['id']}/members/{payer}"), 409, "conflict")
    assert len(client.get(f"/v1/trips/{egypt['id']}").json()["members"]) == 2


def test_member_of_other_trip_not_found(client, egypt, egypt_trip_create):
    other = client.post("/v1/trips", json=egypt_trip_create).json()
    _error(client.delete(f"/v1/trips/{other['id']}/members/{egypt['members'][0]['id']}"), 404, "not_found")


# --- constraints -----------------------------------------------------------


def test_add_and_remove_constraint(client, egypt):
    resp = client.post(f"/v1/trips/{egypt['id']}/constraints", json={"kind": "avoid", "category": "nightclub"})
    assert resp.status_code == 201
    c = resp.json()
    assert (c["kind"], c["hardness"], c["source"], c["locked"]) == ("avoid", "hard", "user", False)
    assert client.get(f"/v1/trips/{egypt['id']}").json()["constraints"][-1] == c
    assert client.delete(f"/v1/trips/{egypt['id']}/constraints/{c['id']}").status_code == 204


def test_invalid_constraint_rejected(client, egypt):
    _error(client.post(f"/v1/trips/{egypt['id']}/constraints", json={"kind": "avoid"}), 422, "validation_error")


# --- bookings --------------------------------------------------------------


BOOKING = {
    "kind": "activity",
    "title": "Karnak sound & light",
    "starts_at": "2026-11-05T19:00:00+02:00",
    "ends_at": "2026-11-05T20:30:00+02:00",
    "stop_seq": 2,
    "cost": {"amount": "25.00", "currency": "USD"},
}


def test_add_and_remove_booking(client, egypt):
    resp = client.post(f"/v1/trips/{egypt['id']}/bookings", json=BOOKING)
    assert resp.status_code == 201
    b = resp.json()
    assert b["starts_at"] == "2026-11-05T17:00:00Z"
    assert b in client.get(f"/v1/trips/{egypt['id']}").json()["bookings"]
    assert client.delete(f"/v1/trips/{egypt['id']}/bookings/{b['id']}").status_code == 204


def test_booking_unknown_stop_rejected(client, egypt):
    _error(client.post(f"/v1/trips/{egypt['id']}/bookings", json={**BOOKING, "stop_seq": 7}), 422, "validation_error")


def test_sub_resource_on_unknown_trip_404(client):
    _error(client.post(f"/v1/trips/{uuid4()}/bookings", json=BOOKING), 404, "not_found")
