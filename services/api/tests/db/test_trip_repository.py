"""CORE-002: Trip aggregate persistence + trips/stops/constraints/bookings constraints (golden slice E1)."""

from datetime import UTC, date, datetime, time

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.models import BookingRow, TripConstraintRow, TripMemberRow, TripRow, TripStopRow, UserRow
from app.db.repositories import TripRepository
from app.domain.trips.models import Trip, TripCreate
from tests.db.test_schema import TRIP_DEFAULTS, _trip


def _reload(session, repo: TripRepository, trip_id) -> Trip:
    session.expire_all()
    loaded = repo.get(trip_id)
    assert loaded is not None
    return loaded


def test_egypt_trip_persists_and_reloads_identically(session, egypt_trip_create):
    """E1: Egypt reference trip saves and reloads identically, without AI."""
    repo = TripRepository(session)
    created = repo.add(TripCreate.model_validate(egypt_trip_create))
    loaded = _reload(session, repo, created.id)
    assert loaded == created
    assert loaded.model_dump(mode="json") == created.model_dump(mode="json")


def test_egypt_rows_land_in_child_tables(session, egypt_trip_create):
    trip = TripRepository(session).add(TripCreate.model_validate(egypt_trip_create))
    count = lambda model: session.scalar(  # noqa: E731
        select(func.count()).select_from(model).where(model.trip_id == trip.id)
    )
    assert (count(TripStopRow), count(TripMemberRow), count(TripConstraintRow), count(BookingRow)) == (3, 2, 3, 6)
    payload = session.scalar(select(TripConstraintRow.payload).where(TripConstraintRow.kind == "time_window"))
    assert payload["label"] == "Collect bags before airport"


def test_minimal_trip_round_trip_with_defaults(session):
    repo = TripRepository(session)
    created = repo.add(
        TripCreate(
            title="Weekend",
            origin="HAN",
            start_date=date(2027, 1, 1),
            end_date=date(2027, 1, 3),
            base_currency="VND",
            stops=[{"city": "Da Lat", "nights": 2}],
        )
    )
    loaded = _reload(session, repo, created.id)
    assert loaded == created
    assert loaded.budget is None and loaded.members == [] and loaded.settlement_currency == "VND"


def test_owner_is_stored(session, egypt_trip_create):
    user = UserRow(display_name="Mia")
    session.add(user)
    session.flush()
    trip = TripRepository(session).add(TripCreate.model_validate(egypt_trip_create), owner_id=user.id)
    assert session.get(TripRow, trip.id).owner_id == user.id


def test_get_unknown_trip_returns_none(session):
    from uuid import uuid4

    assert TripRepository(session).get(uuid4()) is None


def test_delete_cascades_to_children(session, egypt_trip_create):
    repo = TripRepository(session)
    trip = repo.add(TripCreate.model_validate(egypt_trip_create))
    assert repo.delete(trip.id) is True
    for model in (TripStopRow, TripMemberRow, TripConstraintRow, BookingRow):
        assert session.scalar(select(func.count()).select_from(model).where(model.trip_id == trip.id)) == 0
    assert repo.delete(trip.id) is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"end_date": date(2027, 3, 1)},
        {"adults": 0},
        {"adults": 21},
        {"adults": 1, "infants": 2},
        {"adults": 15, "children_ages": [5, 6, 7, 8, 9, 10]},
        {"day_start": time(20), "day_end": time(9)},
        {"price_level": 5},
        {"status": "archived"},
        {"pace": "frantic"},
        {"mobility_needs": "jetpack"},
        {"base_currency": "gbp"},
        {"budget_amount": 100},
        {"budget_amount": 100, "budget_currency": "GBP", "budget_scope": "per_family"},
    ],
    ids=[
        "reversed-dates",
        "zero-adults",
        "too-many-adults",
        "infants-exceed-adults",
        "party-over-20",
        "day-window-reversed",
        "price-level",
        "bad-status",
        "bad-pace",
        "bad-mobility",
        "lowercase-currency",
        "budget-incomplete",
        "bad-budget-scope",
    ],
)
def test_trip_check_constraints(session, overrides):
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            _trip(session, **overrides)


def test_trip_column_defaults(session):
    row = _trip(session)
    session.refresh(row)
    assert (row.status, row.adults, row.infants, row.children_ages, row.pace, row.price_level) == (
        "draft",
        1,
        0,
        [],
        "balanced",
        2,
    )
    assert row.flight_prefs == {} and row.dietary == []


def test_stop_dates_must_match_nights(session):
    trip = _trip(session)
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(
                TripStopRow(
                    trip_id=trip.id,
                    seq=0,
                    city="Cairo",
                    nights=3,
                    arrive_on=date(2027, 3, 14),
                    leave_on=date(2027, 3, 16),
                )
            )
            session.flush()


def test_stop_seq_unique_per_trip(session):
    trip = _trip(session)
    stop = dict(trip_id=trip.id, seq=0, city="Cairo", nights=0, arrive_on=date(2027, 3, 14), leave_on=date(2027, 3, 14))
    session.add(TripStopRow(**stop))
    session.flush()
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(TripStopRow(**{**stop, "city": "Giza"}))
            session.flush()


@pytest.mark.parametrize("kind", ["dietary", "teleport"])
def test_constraint_kind_restricted(session, kind):
    trip = _trip(session)
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(TripConstraintRow(trip_id=trip.id, kind=kind, payload={}))
            session.flush()


@pytest.mark.parametrize(
    "overrides",
    [
        {"ends_at": datetime(2027, 3, 14, 9, tzinfo=UTC)},
        {"cost_amount": 10},
        {"kind": "cruise"},
        {"status": "maybe"},
    ],
    ids=["ends-before-starts", "cost-without-currency", "bad-kind", "bad-status"],
)
def test_booking_check_constraints(session, overrides):
    trip = _trip(session)
    booking = dict(
        trip_id=trip.id,
        kind="hotel",
        title="Hotel",
        starts_at=datetime(2027, 3, 14, 15, tzinfo=UTC),
        ends_at=datetime(2027, 3, 15, 11, tzinfo=UTC),
    )
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(BookingRow(**{**booking, **overrides}))
            session.flush()


def test_member_role_restricted(session):
    trip = _trip(session)
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(TripMemberRow(trip_id=trip.id, display_name="X", role="admin"))
            session.flush()


def test_trip_defaults_fixture_is_valid(session):
    assert _trip(session, **TRIP_DEFAULTS).id
