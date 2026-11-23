"""AI-002: generate / get / diff itinerary against PostGIS."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_planner
from app.db.plans import PlanRepository
from app.db.session import get_session
from app.domain.itinerary.plan import ItemKind, ProposedDay, ProposedItem, ProposedPlan
from app.domain.itinerary.versions import CreatedBy
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


def _gen(client, trip, note=None):
    return client.post(f"/v1/trips/{trip['id']}/itinerary/generate", json={"note": note} if note else None)


def test_no_itinerary_yet(client, trip):
    resp = client.get(f"/v1/trips/{trip['id']}/itinerary")
    assert resp.status_code == 404 and resp.json()["error"]["message"] == "no itinerary yet"


def test_generate_v1_and_reload(client, trip):
    resp = _gen(client, trip, "first draft")
    assert resp.status_code == 201, resp.text
    v1 = resp.json()
    assert (v1["version"], v1["parent_version"], v1["created_by"], v1["planner"]) == (1, None, "planner", "greedy")
    assert v1["reason"] == "first draft" and v1["explanation"]
    assert [d["date"] for d in v1["days"]][0] == "2026-10-31" and len(v1["days"]) == 7
    assert {w["rule"] for w in v1["warnings"]} <= {"V4"}
    assert v1["diff"]["added"] and v1["diff"]["from_version"] is None
    assert client.get(f"/v1/trips/{trip['id']}/itinerary").json() == v1
    assert client.get(f"/v1/trips/{trip['id']}/itinerary?version=1").json() == v1


def test_regenerate_is_stable_and_versions_increase(client, trip):
    v1 = _gen(client, trip).json()
    v2 = _gen(client, trip).json()
    assert (v2["version"], v2["parent_version"]) == (2, 1)
    d = v2["diff"]
    assert (d["added"], d["removed"], d["changed"]) == ([], [], [])  # same proposal → same keys
    assert d["unchanged"] == sum(len(day["items"]) for day in v1["days"])
    assert client.get(f"/v1/trips/{trip['id']}/itinerary/diff").json() == d
    assert client.get(f"/v1/trips/{trip['id']}/itinerary/diff?from=1&to=2").json() == d


def test_generate_keeps_locked_items(client, trip, session):
    v1 = _gen(client, trip).json()
    repo = PlanRepository(session)
    plan = repo.get(trip["id"], 1)
    day = next(d for d in plan.days if str(d.date) == "2026-11-05")
    target = next(i for i in day.items if i.kind is ItemKind.PLACE)
    moved = target.model_copy(update={"locked": True})
    days = [
        d.model_copy(update={"items": [moved if i.item_key == target.item_key else i for i in d.items]})
        for d in plan.days
    ]
    repo.add(
        plan.model_copy(
            update={"version": 2, "parent_version": 1, "created_by": CreatedBy.USER, "days": days, "diff": None}
        )
    )
    resp = _gen(client, trip)
    assert resp.status_code == 201, resp.text
    v3 = resp.json()
    kept = [i for d in v3["days"] for i in d["items"] if i["item_key"] == str(target.item_key)]
    assert len(kept) == 1 and kept[0]["locked"] is True
    assert v3["parent_version"] == 2 and v1["version"] == 1


def test_invalid_plan_is_rejected_and_not_stored(client, trip):
    class Overlapping:
        name = "bad"

        def compose(self, context):
            day = next(d for d in context.days if d.input.window is not None)
            items = [
                ProposedItem(kind="custom", title="A", start="10:00", end="12:00"),
                ProposedItem(kind="custom", title="B", start="11:00", end="13:00"),
            ]
            return ProposedPlan(days=[ProposedDay(date=day.input.date, items=items)])

    app.dependency_overrides[get_planner] = lambda: Overlapping()
    resp = _gen(client, trip)
    assert resp.status_code == 422
    error = resp.json()["error"]
    assert error["message"] == "Plan failed validation"
    assert any(v["rule"] == "V2" for v in error["details"])
    assert client.get(f"/v1/trips/{trip['id']}/itinerary").status_code == 404


def test_diff_unknown_versions(client, trip):
    assert client.get(f"/v1/trips/{trip['id']}/itinerary/diff").status_code == 404
    _gen(client, trip)
    assert client.get(f"/v1/trips/{trip['id']}/itinerary/diff?to=9").status_code == 404
    first = client.get(f"/v1/trips/{trip['id']}/itinerary/diff").json()
    assert first["from_version"] is None and first["added"]


def test_unknown_trip(client):
    assert client.post("/v1/trips/00000000-0000-0000-0000-000000000000/itinerary/generate").status_code == 404
