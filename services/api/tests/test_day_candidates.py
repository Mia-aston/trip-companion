"""ITIN-001 rules on small synthetic trips (A-15)."""

import pytest

from app.domain.itinerary.days import plan_day_inputs
from app.domain.trips.models import Trip, TripCreate
from app.orchestration.day_candidates import build_day_candidates
from app.providers.mock_places import MockPlacesProvider
from app.providers.mock_routes import MockRoutesProvider

BASE = {
    "title": "Luxor weekend",
    "origin": "CAI",
    "start_date": "2026-11-05",
    "end_date": "2026-11-06",
    "base_currency": "EGP",
    "stops": [{"city": "Luxor", "nights": 1, "timezone": "Africa/Cairo"}],
    "interests": ["history"],
}


def _run(**overrides):
    trip = Trip.from_create(TripCreate.model_validate({**BASE, **overrides}))
    return build_day_candidates(trip, MockPlacesProvider(), MockRoutesProvider())


def _names(day):
    return [c.name for c in day.candidates]


@pytest.mark.parametrize(("pace", "capacity"), [("relaxed", 396), ("balanced", 495), ("packed", 594)])
def test_capacity_follows_pace(pace, capacity):
    assert _run(pace=pace).days[0].capacity_minutes == capacity  # 09:00-20:00 = 660 free minutes


def test_mobility_and_young_children_reduce_capacity():
    assert _run(mobility_needs="limited_walking").days[0].capacity_minutes == int(660 * 0.75 * 0.8)
    assert _run(children_ages=[4]).days[0].capacity_minutes == int(660 * 0.75 * 0.85)
    assert _run(children_ages=[9]).days[0].capacity_minutes == 495


def test_wheelchair_drops_inaccessible_places():
    names = _names(_run(mobility_needs="wheelchair").days[0])
    assert "Valley of the Kings" not in names and "Karnak Temple" in names


def test_avoid_by_category_and_query():
    names = _names(
        _run(constraints=[{"kind": "avoid", "category": "museum"}, {"kind": "avoid", "query": "souq"}]).days[0]
    )
    assert "Luxor Museum" not in names and "Luxor Souq" not in names and "Karnak Temple" in names


def test_interest_ranking():
    history = _run().days[0].candidates
    food = _run(interests=["food"]).days[0].candidates
    assert history[0].categories != food[0].categories
    assert "matches your interests" in history[0].reasons


def test_activity_booking_blocks_time():
    booking = {
        "kind": "activity",
        "title": "Nile felucca",
        "starts_at": "2026-11-05T14:00:00+02:00",
        "ends_at": "2026-11-05T16:00:00+02:00",
    }
    day = _run(bookings=[booking]).days[0]
    assert day.free_minutes == 660 - 120
    assert [b.label for b in day.blocked] == ["Nile felucca"]


def test_cancelled_booking_does_not_block():
    booking = {
        "kind": "activity",
        "title": "Cancelled",
        "starts_at": "2026-11-05T14:00:00+02:00",
        "ends_at": "2026-11-05T16:00:00+02:00",
        "status": "cancelled",
    }
    assert _run(bookings=[booking]).days[0].free_minutes == 660


def test_under_an_hour_free_means_no_capacity():
    arrival = {
        "kind": "flight",
        "title": "In",
        "starts_at": "2026-11-05T16:00:00+02:00",
        "ends_at": "2026-11-05T18:00:00+02:00",
    }
    day = _run(bookings=[arrival]).days[0]  # free from 19:30 to 20:00 = 30 min
    assert day.capacity_minutes == 0 and day.candidates == []


def test_unknown_stop_base_is_reported():
    day = _run(stops=[{"city": "Atlantis", "nights": 1}]).days[0]
    assert day.candidates == [] and any("not found" in n for n in day.notes)


def test_unmet_must_do_reported():
    assert _run(constraints=[{"kind": "must_do", "query": "Abu Simbel"}]).unmet_must_dos == ["Abu Simbel"]


def test_pure_function_without_providers_gives_empty_candidates():
    trip = Trip.from_create(TripCreate.model_validate(BASE))
    result = plan_day_inputs(trip, {})
    assert result.days[0].capacity_minutes == 495 and result.days[0].candidates == []
