"""Trip Core rules that need the current trip state (CORE-003). Pure functions: no DB, no I/O."""

from pydantic import ValidationError

from app.domain.shared.errors import Conflict, InvalidChange
from app.domain.trips.models import BookingCreate, MemberCreate, StopCreate, Trip, TripUpdate, derive_stops


def apply_update(trip: Trip, patch: TripUpdate) -> Trip:
    """Merge a PATCH into the trip and re-validate the whole aggregate."""
    changes = patch.model_dump(exclude_unset=True, exclude={"stops"})
    data = trip.model_dump(exclude={"travellers", "stops"}) | changes
    if (
        "base_currency" in changes
        and "settlement_currency" not in changes
        and trip.settlement_currency == trip.base_currency
    ):
        data["settlement_currency"] = changes["base_currency"]  # keep "same as base" when it was implied

    if patch.stops is not None:
        stop_inputs = patch.stops
    else:
        stop_inputs = [StopCreate(**s.model_dump(include=set(StopCreate.model_fields))) for s in trip.stops]

    nights = (data["end_date"] - data["start_date"]).days
    errors = []
    if nights < 0:
        errors.append("end_date must be on or after start_date")
    elif sum(s.nights for s in stop_inputs) != nights:
        errors.append(f"stop nights must sum to the trip length ({nights} nights); send `stops` with the new split")
    if patch.stops is not None:
        dangling = [b.title for b in trip.bookings if b.stop_seq is not None and b.stop_seq >= len(stop_inputs)]
        if dangling:
            errors.append(f"bookings reference removed stops: {', '.join(dangling)}")
    if errors:
        raise InvalidChange("Trip update rejected", errors)

    if patch.stops is not None or data["start_date"] != trip.start_date:
        stops = derive_stops(data["start_date"], stop_inputs)
        if patch.stops is None:  # dates shifted only: keep stop identities
            stops = [s.model_copy(update={"id": old.id}) for s, old in zip(stops, trip.stops, strict=True)]
    else:
        stops = trip.stops

    try:
        return Trip.model_validate({**data, "stops": [s.model_dump() for s in stops]})
    except ValidationError as exc:
        raise InvalidChange("Trip update rejected", [e["msg"] for e in exc.errors()]) from exc


def check_new_member(trip: Trip, member: MemberCreate) -> None:
    if any(m.display_name.casefold() == member.display_name.casefold() for m in trip.members):
        raise Conflict(f"member '{member.display_name}' already exists on this trip")


def check_new_booking(trip: Trip, booking: BookingCreate) -> None:
    if booking.stop_seq is not None and booking.stop_seq >= len(trip.stops):
        raise InvalidChange("Booking rejected", [f"unknown stop_seq {booking.stop_seq}"])
