from datetime import date
from decimal import Decimal

import pytest
from geoalchemy2.functions import ST_Distance, ST_MakePoint, ST_SetSRID
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.models import ExpenseRow, ExpenseShareRow, PlaceRow, TransferRow, TripMemberRow, TripRow
from app.db.repositories import TripRepository
from app.domain.trips.models import Pace, TripCreate


def _trip(session, **overrides) -> TripRow:
    values = dict(origin="London", destination="Cairo", start_date=date(2027, 3, 14), end_date=date(2027, 3, 20))
    row = TripRow(**{**values, **overrides})
    session.add(row)
    session.flush()
    return row


def _members(session, trip: TripRow, *names: str) -> list[TripMemberRow]:
    rows = [TripMemberRow(trip_id=trip.id, display_name=n) for n in names]
    session.add_all(rows)
    session.flush()
    return rows


def _point(lon: float, lat: float):
    return func.ST_GeogFromText(f"SRID=4326;POINT({lon} {lat})")


def test_postgis_extension_installed(session):
    assert session.scalar(select(func.postgis_version()))


@pytest.mark.xfail(strict=True, reason="CORE-002: trips table not yet migrated to the CORE-001 Trip contract")
def test_trip_repository_round_trip(session):
    repo = TripRepository(session)
    created = repo.add(
        TripCreate(
            origin="London",
            destination="Cairo",
            start_date=date(2027, 3, 14),
            end_date=date(2027, 3, 20),
            travellers=3,
            interests=["history", "food"],
            pace=Pace.PACKED,
        )
    )
    session.expire_all()
    loaded = repo.get(created.id)
    assert loaded == created
    assert loaded.pace is Pace.PACKED


def test_trip_defaults(session):
    trip = _trip(session)
    session.refresh(trip)
    assert trip.travellers == 1
    assert trip.interests == []
    assert trip.pace == "balanced"
    assert trip.created_at is not None


@pytest.mark.parametrize(
    "overrides",
    [
        {"end_date": date(2027, 3, 1)},
        {"travellers": 0},
        {"travellers": 21},
        {"pace": "frantic"},
    ],
    ids=["reversed-dates", "zero-travellers", "too-many-travellers", "bad-pace"],
)
def test_trip_check_constraints(session, overrides):
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            _trip(session, **overrides)


def test_member_names_unique_per_trip(session):
    trip = _trip(session)
    _members(session, trip, "An")
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            _members(session, trip, "An")


def test_expense_with_shares_and_transfer(session):
    trip = _trip(session, travellers=2)
    an, binh = _members(session, trip, "An", "Binh")
    expense = ExpenseRow(trip_id=trip.id, description="Dinner", amount=Decimal("40.00"), currency="GBP", payer_id=an.id)
    expense.shares = [
        ExpenseShareRow(member_id=an.id, amount=Decimal("20.00")),
        ExpenseShareRow(member_id=binh.id, amount=Decimal("20.00")),
    ]
    session.add_all(
        [
            expense,
            TransferRow(trip_id=trip.id, sender_id=binh.id, recipient_id=an.id, amount=Decimal("20"), currency="GBP"),
        ]
    )
    session.flush()

    # Transfers live in their own table and never inflate trip cost.
    cost = session.scalar(select(func.sum(ExpenseRow.amount)).where(ExpenseRow.trip_id == trip.id))
    assert cost == Decimal("40.00")
    shares = session.scalar(select(func.sum(ExpenseShareRow.amount)).where(ExpenseShareRow.expense_id == expense.id))
    assert shares == cost


def test_deleting_trip_cascades(session):
    trip = _trip(session)
    (an,) = _members(session, trip, "An")
    session.add(ExpenseRow(trip_id=trip.id, description="Taxi", amount=Decimal("5"), currency="EGP", payer_id=an.id))
    session.flush()
    session.delete(trip)
    session.flush()
    assert session.scalar(select(func.count()).select_from(ExpenseRow)) == 0
    assert session.scalar(select(func.count()).select_from(TripMemberRow)) == 0


@pytest.mark.parametrize("amount", [Decimal("0"), Decimal("-1")])
def test_expense_amount_must_be_positive(session, amount):
    trip = _trip(session)
    (an,) = _members(session, trip, "An")
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(ExpenseRow(trip_id=trip.id, description="x", amount=amount, currency="GBP", payer_id=an.id))
            session.flush()


def test_transfer_to_self_rejected(session):
    trip = _trip(session)
    (an,) = _members(session, trip, "An")
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(
                TransferRow(trip_id=trip.id, sender_id=an.id, recipient_id=an.id, amount=Decimal("1"), currency="GBP")
            )
            session.flush()


def test_places_geography_distance_in_metres(session):
    session.add_all(
        [
            PlaceRow(
                provider="mock", provider_place_id="pyramids", name="Giza Pyramids", location=_point(31.1342, 29.9792)
            ),
            PlaceRow(
                provider="mock", provider_place_id="museum", name="Egyptian Museum", location=_point(31.2336, 30.0478)
            ),
        ]
    )
    session.flush()
    tahrir = ST_SetSRID(ST_MakePoint(31.2357, 30.0444), 4326)
    rows = session.execute(
        select(PlaceRow.name, ST_Distance(PlaceRow.location, func.geography(tahrir)).label("m")).order_by("m")
    ).all()
    assert [r.name for r in rows] == ["Egyptian Museum", "Giza Pyramids"]
    assert rows[0].m < 1_000
    assert 10_000 < rows[1].m < 20_000


def test_place_provider_id_unique(session):
    session.add(PlaceRow(provider="mock", provider_place_id="p1", name="A", location=_point(0, 0)))
    session.flush()
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(PlaceRow(provider="mock", provider_place_id="p1", name="B", location=_point(1, 1)))
            session.flush()


def test_member_with_expenses_cannot_be_deleted(session):
    trip = _trip(session)
    (an,) = _members(session, trip, "An")
    session.add(ExpenseRow(trip_id=trip.id, description="Taxi", amount=Decimal("5"), currency="EGP", payer_id=an.id))
    session.flush()
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.delete(an)
            session.flush()
