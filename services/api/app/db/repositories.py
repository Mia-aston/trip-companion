"""Translate between ORM rows and domain objects. Only this layer touches rows."""

from datetime import time
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db.models import BookingRow, TripConstraintRow, TripMemberRow, TripRow, TripStopRow
from app.domain.shared.errors import Conflict, NotFound
from app.domain.shared.models import Money, TimeWindow
from app.domain.trips.models import (
    Booking,
    Budget,
    Constraint,
    FlightPrefs,
    Member,
    Stop,
    Trip,
    TripCreate,
)

_CONSTRAINT = TypeAdapter(Constraint)
_CONSTRAINT_COLUMNS = {"id", "kind", "hardness", "source", "locked"}


# --- domain -> rows --------------------------------------------------------


def _trip_row(trip: Trip, owner_id: UUID | None) -> TripRow:
    return TripRow(
        id=trip.id,
        owner_id=owner_id,
        **_trip_columns(trip),
        stops=[_stop_row(s) for s in trip.stops],
        members=[_member_row(m, i) for i, m in enumerate(trip.members)],
        constraints=[_constraint_row(c, position) for position, c in enumerate(trip.constraints)],
        bookings=[_booking_row(b) for b in trip.bookings],
    )


def _trip_columns(trip: Trip) -> dict:
    """Scalar trips columns (everything except id/owner and child collections)."""
    budget = trip.budget
    return dict(
        title=trip.title,
        status=trip.status.value,
        origin=trip.origin,
        start_date=trip.start_date,
        end_date=trip.end_date,
        adults=trip.adults,
        children_ages=list(trip.children_ages),
        infants=trip.infants,
        base_currency=trip.base_currency,
        settlement_currency=trip.settlement_currency,
        budget_amount=budget.total.amount if budget else None,
        budget_currency=budget.total.currency if budget else None,
        budget_scope=budget.scope.value if budget else None,
        pace=trip.pace.value,
        day_start=trip.day_window.start,
        day_end=trip.day_window.end,
        interests=[i.value for i in trip.interests],
        dietary=[d.value for d in trip.dietary],
        mobility_needs=trip.mobility_needs.value,
        price_level=trip.price_level,
        flight_prefs=trip.flight_prefs.model_dump(mode="json"),
    )


def _stop_row(s: Stop) -> TripStopRow:
    return TripStopRow(**s.model_dump())


def _member_row(m: Member, position: int) -> TripMemberRow:
    return TripMemberRow(position=position, **m.model_dump())


def _constraint_row(c: Constraint, position: int) -> TripConstraintRow:
    data = c.model_dump(mode="json")
    return TripConstraintRow(
        id=c.id,
        position=position,
        kind=c.kind,
        hardness=c.hardness.value,
        source=c.source.value,
        locked=c.locked,
        payload={k: v for k, v in data.items() if k not in _CONSTRAINT_COLUMNS},
    )


def _booking_row(b: Booking) -> BookingRow:
    data = b.model_dump(exclude={"cost"})
    return BookingRow(
        **data,
        cost_amount=b.cost.amount if b.cost else None,
        cost_currency=b.cost.currency if b.cost else None,
    )


# --- rows -> domain --------------------------------------------------------


def _to_domain(row: TripRow) -> Trip:
    budget = (
        Budget(total=Money(amount=row.budget_amount, currency=row.budget_currency), scope=row.budget_scope)
        if row.budget_amount is not None
        else None
    )
    return Trip(
        id=row.id,
        status=row.status,
        title=row.title,
        origin=row.origin,
        start_date=row.start_date,
        end_date=row.end_date,
        adults=row.adults,
        children_ages=list(row.children_ages),
        infants=row.infants,
        base_currency=row.base_currency,
        settlement_currency=row.settlement_currency,
        budget=budget,
        pace=row.pace,
        day_window=TimeWindow(start=_naive(row.day_start), end=_naive(row.day_end)),
        interests=list(row.interests),
        dietary=list(row.dietary),
        mobility_needs=row.mobility_needs,
        price_level=row.price_level,
        flight_prefs=FlightPrefs.model_validate(row.flight_prefs),
        stops=[
            Stop(
                id=s.id,
                seq=s.seq,
                city=s.city,
                nights=s.nights,
                timezone=s.timezone,
                accommodation_area=s.accommodation_area,
                arrive_on=s.arrive_on,
                leave_on=s.leave_on,
            )
            for s in row.stops
        ],
        members=[
            Member(
                id=m.id,
                user_id=m.user_id,
                display_name=m.display_name,
                role=m.role,
                currency_pref=m.currency_pref,
            )
            for m in row.members
        ],
        constraints=[
            _CONSTRAINT.validate_python(
                {
                    **c.payload,
                    "id": c.id,
                    "kind": c.kind,
                    "hardness": c.hardness,
                    "source": c.source,
                    "locked": c.locked,
                }
            )
            for c in row.constraints
        ],
        bookings=[
            Booking(
                id=b.id,
                kind=b.kind,
                title=b.title,
                starts_at=b.starts_at,
                ends_at=b.ends_at,
                stop_seq=b.stop_seq,
                location_name=b.location_name,
                reference=b.reference,
                cost=Money(amount=b.cost_amount, currency=b.cost_currency) if b.cost_amount is not None else None,
                status=b.status,
            )
            for b in row.bookings
        ],
    )


def _naive(value: time) -> time:
    return value.replace(tzinfo=None)


# --- repository ------------------------------------------------------------


class TripRepository:
    """Persistence for the Trip aggregate (trip + stops + members + constraints + bookings)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, payload: TripCreate, *, owner_id: UUID | None = None) -> Trip:
        trip = Trip.from_create(payload)
        self.session.add(_trip_row(trip, owner_id))
        self.session.flush()
        return trip

    def get(self, trip_id: UUID) -> Trip | None:
        stmt = (
            select(TripRow)
            .where(TripRow.id == trip_id)
            .options(
                selectinload(TripRow.stops),
                selectinload(TripRow.members),
                selectinload(TripRow.constraints),
                selectinload(TripRow.bookings),
            )
            .execution_options(populate_existing=True)
        )
        row = self.session.scalars(stmt).one_or_none()
        return _to_domain(row) if row else None

    def save(self, trip: Trip) -> Trip:
        """Persist scalar fields and stops of an existing trip (PATCH). Child collections use their own methods."""
        row = self._row(trip.id)
        for column, value in _trip_columns(trip).items():
            setattr(row, column, value)
        stored = {s.id: s for s in row.stops}
        if set(stored) == {s.id for s in trip.stops}:
            for stop in trip.stops:  # same stops, dates may have shifted
                for column, value in stop.model_dump(exclude={"id"}).items():
                    setattr(stored[stop.id], column, value)
        else:
            row.stops.clear()
            self.session.flush()  # delete old stops before inserting: (trip_id, seq) is unique
            row.stops.extend(_stop_row(s) for s in trip.stops)
        self.session.flush()
        return trip

    def delete(self, trip_id: UUID) -> bool:
        row = self.session.get(TripRow, trip_id)
        if row is None:
            return False
        self.session.delete(row)
        self.session.flush()
        return True

    # --- child collections ---

    def add_member(self, trip_id: UUID, member: Member) -> Member:
        row = self._row(trip_id)
        row.members.append(_member_row(member, _next_position(row.members)))
        self.session.flush()
        return member

    def remove_member(self, trip_id: UUID, member_id: UUID) -> bool:
        """Raises Conflict when the member is referenced by expenses, shares or transfers."""
        return self._remove(TripMemberRow, trip_id, member_id, in_use="member has expenses or transfers")

    def add_constraint(self, trip_id: UUID, constraint: Constraint) -> Constraint:
        row = self._row(trip_id)
        row.constraints.append(_constraint_row(constraint, _next_position(row.constraints)))
        self.session.flush()
        return constraint

    def remove_constraint(self, trip_id: UUID, constraint_id: UUID) -> bool:
        return self._remove(TripConstraintRow, trip_id, constraint_id)

    def add_booking(self, trip_id: UUID, booking: Booking) -> Booking:
        row = self._row(trip_id)  # keep a strong reference until flush
        row.bookings.append(_booking_row(booking))
        self.session.flush()
        return booking

    def remove_booking(self, trip_id: UUID, booking_id: UUID) -> bool:
        return self._remove(BookingRow, trip_id, booking_id)

    # --- helpers ---

    def _row(self, trip_id: UUID) -> TripRow:
        row = self.session.get(TripRow, trip_id)
        if row is None:
            raise NotFound(f"trip {trip_id} not found")
        return row

    def _remove(self, model, trip_id: UUID, child_id: UUID, *, in_use: str = "") -> bool:
        child = self.session.get(model, child_id)
        if child is None or child.trip_id != trip_id:
            return False
        try:
            with self.session.begin_nested():
                self.session.delete(child)
                self.session.flush()
        except IntegrityError as exc:
            raise Conflict(in_use or "still referenced") from exc
        return True


def _next_position(rows) -> int:
    return max((r.position for r in rows), default=-1) + 1
