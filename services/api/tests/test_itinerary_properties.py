"""Property tests (TESTING.md): validator never accepts overlaps; GreedyPlanner output always validates."""

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.domain.itinerary.days import DayPlanInput
from app.domain.itinerary.plan import ItemKind, ItemSource, PlanDay, PlanItem
from app.domain.itinerary.planner import GreedyPlanner
from app.domain.itinerary.validator import Severity, has_errors, validate
from app.domain.shared.models import TimeWindow
from app.domain.trips.models import Trip, TripCreate
from app.orchestration.itinerary import plan_trip
from app.providers.mock_places import MockPlacesProvider
from app.providers.mock_routes import MockRoutesProvider

DAY = date(2026, 11, 5)
TRIP = Trip.from_create(
    TripCreate(
        title="P",
        origin="X",
        start_date=DAY,
        end_date=DAY,
        base_currency="EGP",
        stops=[{"city": "Luxor", "nights": 0, "timezone": "UTC"}],
    )
)
WIDE = DayPlanInput(
    date=DAY,
    stop_seq=0,
    city="Luxor",
    timezone="UTC",
    window=TimeWindow(start="00:00", end="23:59"),
    blocked=[],
    free_minutes=1439,
    capacity_minutes=1439,
    candidates=[],
    notes=[],
)

intervals = st.lists(st.tuples(st.integers(0, 1380), st.integers(15, 120)), min_size=1, max_size=8)


@given(intervals)
def test_overlap_reported_iff_present(spans):
    base = datetime(2026, 11, 5, tzinfo=UTC)
    items = [
        PlanItem(
            item_key=uuid4(),
            kind=ItemKind.CUSTOM,
            title=f"i{n}",
            source=ItemSource.USER,
            starts_at=base + timedelta(minutes=s),
            ends_at=base + timedelta(minutes=min(s + d, 1439)),
        )
        for n, (s, d) in enumerate(spans)
    ]
    plan = [PlanDay(date=DAY, stop_seq=0, timezone="UTC", items=items)]
    violations = validate(TRIP, plan, {DAY: WIDE}, {}, lambda a, b: None)
    ordered = sorted(items, key=lambda i: (i.starts_at, i.ends_at))
    overlapping = any(b.starts_at < a.ends_at for a, b in zip(ordered, ordered[1:], strict=False))
    assert any(v.rule == "V2" and v.severity is Severity.ERROR for v in violations) == overlapping


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    pace=st.sampled_from(["relaxed", "balanced", "packed"]),
    interests=st.lists(st.sampled_from(["history", "food", "photo", "shopping", "nature"]), unique=True, max_size=3),
    mobility=st.sampled_from(["none", "limited_walking", "wheelchair"]),
    nights=st.integers(0, 3),
    start_hour=st.integers(6, 11),
    activity=st.one_of(st.none(), st.tuples(st.integers(8, 18), st.integers(1, 3))),
    must_do=st.sampled_from([None, "Karnak", "Valley of the Kings", "Luxor Museum"]),
)
def test_greedy_plans_always_validate(pace, interests, mobility, nights, start_hour, activity, must_do):
    end = DAY + timedelta(days=nights)
    payload = {
        "title": "Luxor",
        "origin": "CAI",
        "start_date": DAY.isoformat(),
        "end_date": end.isoformat(),
        "base_currency": "EGP",
        "pace": pace,
        "interests": interests,
        "mobility_needs": mobility,
        "day_window": {"start": f"{start_hour:02d}:00", "end": "21:00"},
        "stops": [{"city": "Luxor", "nights": nights, "timezone": "Africa/Cairo"}],
    }
    if activity:
        h, length = activity
        payload["bookings"] = [
            {
                "kind": "activity",
                "title": "Felucca",
                "starts_at": f"{DAY}T{h:02d}:00:00+02:00",
                "ends_at": f"{DAY}T{h + length:02d}:00:00+02:00",
            }
        ]
    if must_do:
        payload["constraints"] = [{"kind": "must_do", "query": must_do}]
    trip = Trip.from_create(TripCreate.model_validate(payload))
    result = plan_trip(trip, MockPlacesProvider(), MockRoutesProvider(), GreedyPlanner())
    assert not has_errors(result.violations), [v.message for v in result.violations if v.severity is Severity.ERROR]


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(pick=st.integers(0, 50), pace=st.sampled_from(["relaxed", "balanced", "packed"]))
def test_replanning_around_a_locked_item_stays_valid(pick, pace):
    """Regression: travel time to/from kept (locked) visits must be respected (found in AI-002)."""
    from app.domain.itinerary.versions import kept_items

    payload = {
        "title": "Luxor",
        "origin": "CAI",
        "start_date": DAY.isoformat(),
        "end_date": (DAY + timedelta(days=1)).isoformat(),
        "base_currency": "EGP",
        "pace": pace,
        "interests": ["history"],
        "stops": [{"city": "Luxor", "nights": 1, "timezone": "Africa/Cairo"}],
    }
    trip = Trip.from_create(TripCreate.model_validate(payload))
    first = plan_trip(trip, MockPlacesProvider(), MockRoutesProvider(), GreedyPlanner())
    visits = [(d, i) for d in first.plan for i in d.items if i.kind is ItemKind.PLACE]
    d, target = visits[pick % len(visits)]
    locked = [
        x.model_copy(
            update={
                "items": [
                    i.model_copy(update={"locked": True}) if i.item_key == target.item_key else i for i in x.items
                ]
            }
        )
        for x in first.plan
    ]
    second = plan_trip(
        trip, MockPlacesProvider(), MockRoutesProvider(), GreedyPlanner(), keep=kept_items(locked), previous=locked
    )
    assert not has_errors(second.violations), [v.message for v in second.violations if v.severity is Severity.ERROR]
