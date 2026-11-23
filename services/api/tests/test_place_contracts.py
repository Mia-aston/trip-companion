from datetime import datetime, time

import pytest
from pydantic import ValidationError

from app.domain.places.models import OpeningPeriod, Place, is_open_for, open_intervals
from app.providers.mock_places import MockPlacesProvider

PROVENANCE = {"source": "provider", "provider": "mock", "fetched_at": "2026-11-23T00:00:00Z"}


def _place(**overrides) -> Place:
    data = {
        "id": "mock:x",
        "provider": "mock",
        "provider_place_id": "x",
        "name": "X",
        "location": {"lat": 30, "lon": 31},
        "timezone": "Africa/Cairo",
        "provenance": PROVENANCE,
    }
    return Place.model_validate({**data, **overrides})


def test_all_fixtures_are_valid_places():
    places = MockPlacesProvider().search("", MockPlacesProvider().resolve_city("Cairo").location, radius_m=2_000_000)
    assert len(places) == 21


def test_id_must_match_provider_and_source_id():
    with pytest.raises(ValidationError):
        _place(id="mock:y")


def test_provider_provenance_required():
    with pytest.raises(ValidationError):
        _place(provenance={"source": "provider", "provider": "mock"})


@pytest.mark.parametrize(
    "bad", [{"rating": 5.5}, {"price_level": 0}, {"typical_visit_minutes": 0}, {"categories": ["zoo"]}]
)
def test_invalid_fields(bad):
    with pytest.raises(ValidationError):
        _place(**bad)


def test_hours_unknown_vs_never_open():
    assert is_open_for(_place(), datetime(2026, 11, 2, 10), 60) is None
    assert is_open_for(_place(opening_hours=[]), datetime(2026, 11, 2, 10), 60) is False


def test_open_for_whole_visit_only():
    museum = _place(opening_hours=[OpeningPeriod(weekday=d, open=time(9), close=time(17)) for d in range(7)])
    monday = datetime(2026, 11, 2)
    assert is_open_for(museum, monday.replace(hour=9), 120)
    assert not is_open_for(museum, monday.replace(hour=16), 120)  # would close mid-visit
    assert not is_open_for(museum, monday.replace(hour=8, minute=30), 60)


def test_closed_weekday():
    coptic = MockPlacesProvider().details("mock:coptic-cairo")  # closed Mondays
    assert not is_open_for(coptic, datetime(2026, 11, 2, 10), 60)  # Monday
    assert is_open_for(coptic, datetime(2026, 11, 1, 10), 60)  # Sunday


def test_period_past_midnight_counts_on_next_morning():
    club = MockPlacesProvider().details("mock:nile-nightclub")  # Thu/Fri/Sat 22:00-03:00
    assert is_open_for(club, datetime(2026, 11, 6, 1), 60)  # Friday 01:00 ← Thursday night
    assert is_open_for(club, datetime(2026, 11, 5, 23), 60)  # Thursday 23:00
    assert not is_open_for(club, datetime(2026, 11, 4, 23), 60)  # Wednesday


def test_split_hours():
    museum = MockPlacesProvider().details("mock:luxor-museum")  # 09-14, 17-21
    intervals = open_intervals(museum, datetime(2026, 11, 5))
    assert [(a.hour, b.hour) for a, b in intervals] == [(9, 14), (17, 21)]
    assert not is_open_for(museum, datetime(2026, 11, 5, 13), 90)
