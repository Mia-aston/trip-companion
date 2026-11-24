"""Select a flight offer for a trip (FLIGHT-004, A-23/A-24): offer snapshot → tentative flight booking."""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from pydantic import Field

from app.db.flights import FlightSnapshots
from app.db.repositories import TripRepository
from app.domain.flights.models import Direction, FlightOffer
from app.domain.itinerary.days import arrival_departure
from app.domain.shared.errors import Conflict, InvalidChange, NotFound
from app.domain.shared.models import Contract
from app.domain.trips.models import Booking, BookingKind, BookingStatus, Trip
from app.orchestration.itinerary import workspace
from app.providers.base import PlacesProvider, RoutesProvider


class SelectOffer(Contract):
    offer_id: str = Field(min_length=3, max_length=300, examples=["mock:nm780-20261031-2a0c0i"])


class SelectResult(Contract):
    direction: Direction
    booking: Booking
    replaced_booking_id: UUID | None = None
    affected_dates: list[date] = Field(
        description="Days whose sightseeing window or capacity changed — consider re-planning"
    )


def _booking(offer: FlightOffer) -> Booking:
    first, last = offer.segments[0], offer.segments[-1]
    numbers = " + ".join(s.flight_number for s in offer.segments)
    return Booking(
        id=uuid4(),
        kind=BookingKind.FLIGHT,
        title=f"{first.carrier_name} {numbers} {first.origin}→{last.destination}"[:120],
        starts_at=offer.departs_at,
        ends_at=offer.arrives_at,
        location_name=f"{first.origin}→{last.destination}",
        reference=offer.offer_id[:120],
        cost=offer.total,
        status=BookingStatus.TENTATIVE,
    )


def _check_fits(trip: Trip, direction: Direction, offer: FlightOffer) -> None:
    if direction is Direction.OUTBOUND:
        last = offer.segments[-1]
        lands = offer.arrives_at.astimezone(ZoneInfo(last.destination_timezone)).date()
        if not trip.start_date <= lands <= trip.end_date:
            raise InvalidChange(
                "Flight rejected", [f"outbound lands {lands}, outside the trip ({trip.start_date}–{trip.end_date})"]
            )
    else:
        first = offer.segments[0]
        leaves = offer.departs_at.astimezone(ZoneInfo(first.origin_timezone)).date()
        if not trip.start_date <= leaves <= trip.end_date:
            raise InvalidChange(
                "Flight rejected", [f"return departs {leaves}, outside the trip ({trip.start_date}–{trip.end_date})"]
            )


def select_offer(
    trip: Trip,
    offer_id: str,
    trips: TripRepository,
    snapshots: FlightSnapshots,
    places: PlacesProvider,
    routes: RoutesProvider,
    now: datetime | None = None,
) -> SelectResult:
    now = now or datetime.now(UTC)
    found = snapshots.latest(trip.id, offer_id)
    if found is None:
        raise NotFound(f"offer {offer_id} was not returned by a search for this trip")
    direction, offer, row = found
    if offer.expired(now):
        raise Conflict("Offer expired — search again", [f"expired at {offer.expires_at.isoformat()}"])
    _check_fits(trip, direction, offer)

    before = {d: (i.window, i.capacity_minutes) for d, i in workspace(trip, places, routes).day_inputs.items()}
    arrival, departure = arrival_departure(trip)
    replaced = arrival if direction is Direction.OUTBOUND else departure
    if replaced is not None:
        trips.remove_booking(trip.id, replaced.id)
    booking = trips.add_booking(trip.id, _booking(offer))
    row.selected_at = now

    updated = trips.get(trip.id)
    after = {d: (i.window, i.capacity_minutes) for d, i in workspace(updated, places, routes).day_inputs.items()}
    affected = sorted(d for d in after if after[d] != before.get(d))
    return SelectResult(
        direction=direction,
        booking=booking,
        replaced_booking_id=replaced.id if replaced else None,
        affected_dates=affected,
    )
