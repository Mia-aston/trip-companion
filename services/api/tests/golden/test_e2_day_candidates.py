"""Golden slice E2 (docs/TESTING.md): feasible day candidates with travel times for the Egypt trip."""

from datetime import date, time

import pytest

from app.domain.trips.models import Trip, TripCreate
from app.orchestration.day_candidates import build_day_candidates
from app.providers.mock_places import MockPlacesProvider
from app.providers.mock_routes import MockRoutesProvider


@pytest.fixture
def result(egypt_trip_create):
    trip = Trip.from_create(TripCreate.model_validate(egypt_trip_create))
    return build_day_candidates(trip, MockPlacesProvider(), MockRoutesProvider())


def _day(result, d: date):
    return next(x for x in result.days if x.date == d)


def test_every_trip_date_has_a_day(result):
    assert [d.date for d in result.days] == [date(2026, 10, 31 + i) if i == 0 else date(2026, 11, i) for i in range(7)]
    assert [d.city for d in result.days] == ["Cairo"] * 3 + ["Western Desert"] + ["Luxor"] * 3


def test_late_arrival_day_has_no_sightseeing(result):
    day = _day(result, date(2026, 10, 31))
    assert day.capacity_minutes == 0 and day.window is None and day.candidates == []


def test_departure_day_cut_off_before_airport(result):
    day = _day(result, date(2026, 11, 6))
    assert day.window.end == time(19, 30)  # 22:30 flight − 180 min
    assert day.capacity_minutes > 0


def test_transfer_day_starts_after_train(result):
    day = _day(result, date(2026, 11, 4))
    assert day.window.start == time(19, 0)
    assert all(c.travel_minutes * 2 + c.visit_minutes <= day.capacity_minutes for c in day.candidates if c.fits)


def test_giza_must_do_on_a_cairo_day(result):
    cairo_days = [d for d in result.days if d.city == "Cairo" and d.capacity_minutes]
    giza = [c for d in cairo_days for c in d.candidates if c.name == "Giza Pyramids"]
    assert giza and all(c.must_do and c.fits for c in giza)
    assert all(d.candidates[0].name == "Giza Pyramids" for d in cairo_days)  # ranked first
    assert result.unmet_must_dos == []  # balloon is covered by its booking


def test_closed_places_never_appear(result):
    monday = _day(result, date(2026, 11, 2))
    assert "Coptic Cairo" not in [c.name for c in monday.candidates]
    assert "Coptic Cairo" in [c.name for c in _day(result, date(2026, 11, 1)).candidates]
    for d in result.days:
        assert "Nile Nightclub" not in [c.name for c in d.candidates]  # only open 22:00-03:00


def test_candidates_have_travel_times_and_reasons(result):
    for d in result.days:
        for c in d.candidates:
            assert c.travel_minutes >= 0 and c.reasons
            assert c.reasons[-1].endswith(f"from {d.city}") or "from" in c.reasons[-1]
