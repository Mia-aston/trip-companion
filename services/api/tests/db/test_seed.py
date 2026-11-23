"""CORE-004: Egypt seed is idempotent and loads the full golden trip."""

import sys
from pathlib import Path

from app.db.repositories import TripRepository

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from seed_egypt import egypt_payload, seed  # noqa: E402


def test_seed_creates_full_trip(session):
    trip_id, created = seed(session)
    assert created
    trip = TripRepository(session).get(trip_id)
    assert (len(trip.stops), len(trip.members), len(trip.constraints), len(trip.bookings)) == (3, 2, 3, 6)
    assert trip.title == egypt_payload().title


def test_seed_is_idempotent(session):
    first, _ = seed(session)
    again, created = seed(session)
    assert (again, created) == (first, False)


def test_seed_reset_recreates(session):
    first, _ = seed(session)
    second, created = seed(session, reset=True)
    assert created and second != first
    assert TripRepository(session).get(first) is None
