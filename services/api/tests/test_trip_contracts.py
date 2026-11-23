from datetime import date

import pytest
from pydantic import ValidationError

from app.domain.trips.models import Trip, TripCreate, TripUpdate


def test_egypt_fixture_is_valid(egypt_trip_create):
    trip = TripCreate.model_validate(egypt_trip_create)
    assert trip.travellers == 2
    assert [s.city for s in trip.stops] == ["Cairo", "Western Desert", "Luxor"]
    assert {c.kind for c in trip.constraints} == {"must_do", "time_window"}


def test_from_create_derives_stop_dates(egypt_trip_create):
    trip = Trip.from_create(TripCreate.model_validate(egypt_trip_create))
    assert [(s.seq, s.arrive_on, s.leave_on) for s in trip.stops] == [
        (0, date(2026, 10, 31), date(2026, 11, 3)),
        (1, date(2026, 11, 3), date(2026, 11, 4)),
        (2, date(2026, 11, 4), date(2026, 11, 6)),
    ]
    assert trip.status == "draft"
    assert len({m.id for m in trip.members}) == 2
    assert all(c.source == "user" and not c.locked for c in trip.constraints)


def test_trip_json_round_trip(egypt_trip_create):
    trip = Trip.from_create(TripCreate.model_validate(egypt_trip_create))
    assert Trip.model_validate_json(trip.model_dump_json(exclude={"travellers"})) == trip


def test_minimal_trip_defaults():
    trip = TripCreate(
        title="Weekend",
        origin="HAN",
        start_date=date(2027, 1, 1),
        end_date=date(2027, 1, 3),
        base_currency="VND",
        stops=[{"city": "Da Lat", "nights": 2}],
    )
    assert trip.adults == 1 and trip.travellers == 1
    assert trip.settlement_currency == "VND"
    assert trip.pace == "balanced" and trip.price_level == 2
    assert (trip.day_window.start.hour, trip.day_window.end.hour) == (9, 20)
    assert trip.flight_prefs.cabin == "economy"


def _invalid(egypt: dict, **changes) -> dict:
    return {**egypt, **changes}


@pytest.mark.parametrize(
    "changes",
    [
        {"end_date": "2026-10-30"},
        {"stops": [{"city": "Cairo", "nights": 2}]},
        {"adults": 0},
        {"adults": 1, "infants": 2},
        {"adults": 15, "children_ages": [5, 6, 7, 8, 9, 10]},
        {"children_ages": [1]},
        {"interests": ["history", "history"]},
        {"interests": ["sightseeing"]},
        {"dietary": ["paleo"]},
        {"members": [{"display_name": "Mia"}, {"display_name": "mia"}]},
        {"constraints": [{"kind": "must_do"}]},
        {"constraints": [{"kind": "teleport", "query": "x"}]},
        {
            "bookings": [
                {"kind": "hotel", "title": "x", "starts_at": "2026-11-01T10:00:00", "ends_at": "2026-11-02T10:00:00"}
            ]
        },
        {
            "bookings": [
                {
                    "kind": "hotel",
                    "title": "x",
                    "starts_at": "2026-11-01T10:00:00Z",
                    "ends_at": "2026-11-02T10:00:00Z",
                    "stop_seq": 9,
                }
            ]
        },
        {"stops": [{"city": "Cairo", "nights": 6, "timezone": "Mars/Base"}]},
        {"price_level": 5},
        {"surprise": True},
    ],
    ids=[
        "end-before-start",
        "nights-mismatch",
        "no-adults",
        "infants-exceed-adults",
        "over-20-travellers",
        "child-under-2",
        "duplicate-interest",
        "unknown-interest",
        "unknown-dietary",
        "duplicate-member",
        "must-do-without-target",
        "unknown-constraint-kind",
        "naive-booking-time",
        "booking-unknown-stop",
        "bad-timezone",
        "price-level-out-of-range",
        "unknown-field",
    ],
)
def test_trip_create_rejects(egypt_trip_create, changes):
    with pytest.raises(ValidationError):
        TripCreate.model_validate(_invalid(egypt_trip_create, **changes))


def test_trip_update_is_partial():
    patch = TripUpdate.model_validate({"pace": "relaxed"})
    assert patch.model_dump(exclude_unset=True) == {"pace": "relaxed"}
    with pytest.raises(ValidationError):
        TripUpdate.model_validate({"stops": []})
