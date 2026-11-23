"""AI-001 plan contracts + ITIN-002 validator rules + GreedyPlanner on the Egypt trip."""

import json
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.itinerary.plan import ItemKind, ItemSource, PlanItem, ProposedItem, booking_item_key
from app.domain.itinerary.planner import GreedyPlanner
from app.domain.itinerary.validator import Severity, has_errors, shift, validate
from app.domain.trips.models import Avoid, Trip, TripCreate
from app.orchestration.itinerary import plan_trip
from app.providers.mock_places import MockPlacesProvider
from app.providers.mock_routes import MockRoutesProvider

FIXTURE = Path(__file__).parent / "fixtures" / "egypt" / "trip_create.json"


@pytest.fixture(scope="module")
def egypt():
    trip = Trip.from_create(TripCreate.model_validate(json.loads(FIXTURE.read_text())))
    return trip, plan_trip(trip, MockPlacesProvider(), MockRoutesProvider(), GreedyPlanner())


def _rules(trip, result, plan, previous=None):
    def travel(a, b):
        return MockRoutesProvider().matrix([w for w in _waypoints(result) if w.id in (a, b)], "drive").minutes(a, b)

    return {(v.rule, v.severity) for v in validate(trip, plan, result.day_inputs, result.places, travel, previous)}


def _waypoints(result):
    from app.domain.routing.models import Waypoint

    return [Waypoint(id=p.id, location=p.location) for p in result.places.values()]


def _day(plan, d: date):
    return next(x for x in plan if x.date == d)


def _replace_day(plan, d: date, items):
    return [x.model_copy(update={"items": items}) if x.date == d else x for x in plan]


# --- contracts ---------------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        {"kind": "place", "title": "x", "place_id": "mock:x", "start": "10:00", "end": "09:00"},
        {"kind": "place", "title": "x", "start": "10:00", "end": "11:00"},
        {"kind": "booking", "title": "x", "start": "10:00", "end": "11:00"},
    ],
    ids=["end-before-start", "place-without-id", "planner-booking"],
)
def test_proposed_item_rejects(bad):
    with pytest.raises(ValidationError):
        ProposedItem.model_validate(bad)


def test_booking_items_are_locked_with_stable_keys(egypt):
    trip, result = egypt
    bookings = [i for d in result.plan for i in d.items if i.kind is ItemKind.BOOKING]
    assert {b.title for b in bookings} == {
        "Arrival flight to Cairo",
        "Railway to Luxor",
        "Hot air balloon",
        "Departure flight from Luxor",
    }  # hotels are day context, not items
    assert all(b.locked and b.source is ItemSource.BOOKING for b in bookings)
    assert all(b.item_key == booking_item_key(trip, b.booking_id) for b in bookings)


def test_planner_times_are_local_and_stored_utc(egypt):
    _, result = egypt
    giza = next(i for d in result.plan for i in d.items if i.title == "Giza Pyramids")
    day = _day(result.plan, giza.starts_at.date())
    assert giza.starts_at.tzinfo is not None
    assert day.local(giza.starts_at).time() >= time(8, 0)  # inside the 08:00-21:00 local window


# --- greedy plan on Egypt -------------------------------------------------------


def test_egypt_greedy_plan_has_no_errors(egypt):
    _, result = egypt
    assert not has_errors(result.violations), result.violations
    assert {v.rule for v in result.violations} <= {"V4"}  # only "hours unknown" for the White Desert


def test_egypt_plan_shape(egypt):
    _, result = egypt
    places = [i.place_id for d in result.plan for i in d.items if i.kind is ItemKind.PLACE]
    assert len(places) == len(set(places)), "a place is visited once per trip"
    assert "mock:giza-pyramids" in places
    assert [i for i in _day(result.plan, date(2026, 10, 31)).items if i.kind is not ItemKind.BOOKING] == []
    last = _day(result.plan, date(2026, 11, 6))
    assert all(last.local(i.ends_at).time() <= time(19, 30) for i in last.items if i.kind is not ItemKind.BOOKING)
    assert any(i.kind is ItemKind.MEAL for i in _day(result.plan, date(2026, 11, 1)).items)


# --- each rule fires on a broken plan --------------------------------------------


def _first_place(plan, d: date):
    return next(i for i in _day(plan, d).items if i.kind is ItemKind.PLACE)


def test_v1_outside_window(egypt):
    trip, result = egypt
    d = date(2026, 11, 1)
    item = _first_place(result.plan, d)
    early = item.model_copy(
        update={"starts_at": item.starts_at.replace(hour=4), "ends_at": item.ends_at.replace(hour=5)}
    )
    plan = _replace_day(
        result.plan, d, [early if i.item_key == item.item_key else i for i in _day(result.plan, d).items]
    )
    assert ("V1", Severity.ERROR) in _rules(trip, result, plan)


def test_v1_item_on_day_without_time(egypt):
    trip, result = egypt
    d = date(2026, 10, 31)
    extra = PlanItem(
        item_key=uuid4(),
        kind=ItemKind.CUSTOM,
        title="Late walk",
        source=ItemSource.USER,
        starts_at=datetime(2026, 10, 31, 20, tzinfo=UTC),
        ends_at=datetime(2026, 10, 31, 21, tzinfo=UTC),
    )
    plan = _replace_day(result.plan, d, _day(result.plan, d).items + [extra])
    assert ("V1", Severity.ERROR) in _rules(trip, result, plan)


def test_v2_overlap_and_v3_travel(egypt):
    trip, result = egypt
    d = date(2026, 11, 1)
    items = _day(result.plan, d).items
    places = [i for i in items if i.kind is ItemKind.PLACE]
    moved = shift(places[1], -(places[1].starts_at - places[0].ends_at).seconds // 60)  # starts right when #1 ends
    plan = _replace_day(result.plan, d, [moved if i.item_key == moved.item_key else i for i in items])
    rules = _rules(trip, result, plan)
    assert ("V3", Severity.ERROR) in rules or ("V2", Severity.ERROR) in rules


def test_v4_closed(egypt):
    trip, result = egypt
    d = date(2026, 11, 2)  # Monday: Coptic Cairo closed
    coptic = PlanItem(
        item_key=uuid4(),
        kind=ItemKind.PLACE,
        title="Coptic Cairo",
        place_id="mock:coptic-cairo",
        source=ItemSource.USER,
        starts_at=datetime(2026, 11, 2, 16, tzinfo=UTC),
        ends_at=datetime(2026, 11, 2, 17, tzinfo=UTC),
    )
    plan = _replace_day(result.plan, d, _day(result.plan, d).items + [coptic])
    assert ("V4", Severity.ERROR) in _rules(trip, result, plan)


def test_v5_missing_and_moved_booking(egypt):
    trip, result = egypt
    d = date(2026, 11, 4)
    items = _day(result.plan, d).items
    without = [i for i in items if i.kind is not ItemKind.BOOKING]
    assert ("V5", Severity.ERROR) in _rules(trip, result, _replace_day(result.plan, d, without))
    moved = [shift(i, 30) if i.kind is ItemKind.BOOKING else i for i in items]
    assert ("V5", Severity.ERROR) in _rules(trip, result, _replace_day(result.plan, d, moved))


def test_v6_locked_item_changed(egypt):
    trip, result = egypt
    d = date(2026, 11, 5)
    item = _first_place(result.plan, d).model_copy(update={"locked": True})
    previous = _replace_day(
        result.plan, d, [item if i.item_key == item.item_key else i for i in _day(result.plan, d).items]
    )
    current = _replace_day(previous, d, [i for i in _day(previous, d).items if i.item_key != item.item_key])
    assert ("V6", Severity.ERROR) in _rules(trip, result, current, previous)
    assert ("V6", Severity.ERROR) not in _rules(trip, result, previous, previous)


def test_v7_must_do_missing(egypt):
    trip, result = egypt
    plan = [
        d.model_copy(update={"items": [i for i in d.items if i.place_id != "mock:giza-pyramids"]}) for d in result.plan
    ]
    assert ("V7", Severity.WARNING) in _rules(trip, result, plan)


def test_v8_avoided_place(egypt):
    trip, result = egypt
    avoid = trip.model_copy(update={"constraints": [*trip.constraints, Avoid(id=uuid4(), query="Giza")]})
    assert ("V8", Severity.ERROR) in _rules(avoid, result, result.plan)


def test_v9_over_capacity(egypt):
    trip, result = egypt
    d = date(2026, 11, 4)  # 90 min capacity
    long = PlanItem(
        item_key=uuid4(),
        kind=ItemKind.PLACE,
        title="Luxor Temple",
        place_id="mock:luxor-temple",
        source=ItemSource.USER,
        starts_at=datetime(2026, 11, 4, 17, 0, tzinfo=UTC),
        ends_at=datetime(2026, 11, 4, 17, 0, tzinfo=UTC) + timedelta(minutes=120),
    )
    plan = _replace_day(
        result.plan, d, [i for i in _day(result.plan, d).items if i.kind is not ItemKind.PLACE] + [long]
    )
    assert ("V9", Severity.WARNING) in _rules(trip, result, plan)
