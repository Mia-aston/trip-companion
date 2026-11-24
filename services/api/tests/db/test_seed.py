"""CORE-004: Egypt seed is idempotent and loads the full golden trip."""

import sys
from pathlib import Path

from app.db.repositories import TripRepository

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from seed_egypt import DEMO_TRIP_ID, egypt_payload, seed  # noqa: E402


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


def test_seed_uses_stable_demo_id(session):
    trip_id, _ = seed(session)
    assert trip_id == DEMO_TRIP_ID


def test_seed_reset_recreates(session):
    repo = TripRepository(session)
    first, _ = seed(session)
    repo.add_member(
        first,
        __import__("app.domain.trips.models", fromlist=["Member"]).Member(
            id=__import__("uuid").uuid4(), display_name="Extra"
        ),
    )
    second, created = seed(session, reset=True)
    assert created and second == first == DEMO_TRIP_ID
    assert [m.display_name for m in repo.get(second).members] == ["Mia", "QA"]  # back to the fixture
