from datetime import date, time
from decimal import Decimal

import pytest
from geoalchemy2.functions import ST_Distance, ST_MakePoint, ST_SetSRID
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.models import ExpenseRow, ExpenseShareRow, PlaceRow, TransferRow, TripMemberRow, TripRow

TRIP_DEFAULTS = dict(
    title="Test trip",
    origin="London",
    start_date=date(2027, 3, 14),
    end_date=date(2027, 3, 20),
    base_currency="GBP",
    settlement_currency="GBP",
    day_start=time(9),
    day_end=time(20),
)


def _trip(session, **overrides) -> TripRow:
    row = TripRow(**{**TRIP_DEFAULTS, **overrides})
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


def test_member_names_unique_per_trip_case_insensitive(session):
    trip = _trip(session)
    _members(session, trip, "An")
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            _members(session, trip, "an")


def test_expense_with_shares_and_transfer(session):
    trip = _trip(session, adults=2)
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
