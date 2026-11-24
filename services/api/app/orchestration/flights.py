"""Flight search for a trip (FLIGHT-002): build the search from the trip, call the provider, filter, snapshot."""

from datetime import UTC, datetime
from datetime import date as Date
from typing import Self
from uuid import UUID, uuid4

from pydantic import Field, ValidationError, model_validator

from app.db.flights import FlightSnapshots
from app.domain.flights.models import AirportCode, Direction, FlightOffer, FlightSearch, SortBy, filter_and_sort
from app.domain.shared.errors import InvalidChange
from app.domain.shared.models import Contract, UtcDatetime
from app.domain.trips.models import CabinClass, Trip
from app.providers.base import FlightProvider


class TripFlightSearch(Contract):
    """Request body. Passengers always come from the trip; preferences default to the trip's `flight_prefs`."""

    direction: Direction
    from_airport: AirportCode
    to_airport: AirportCode
    date: Date | None = Field(default=None, description="Defaults to the trip start (outbound) or end (return) date")
    cabin: CabinClass | None = None
    max_stops: int | None = Field(default=None, ge=0, le=3)
    checked_bags: int | None = Field(default=None, ge=0, le=3)
    sort: SortBy = SortBy.PRICE

    @model_validator(mode="after")
    def airports_differ(self) -> Self:
        if self.from_airport == self.to_airport:
            raise ValueError("from and to airports must differ")
        return self


class FlightSearchResult(Contract):
    search_id: UUID
    search: FlightSearch
    offers: list[FlightOffer]
    searched_at: UtcDatetime
    filtered_out: int = Field(description="Offers dropped by cabin / stops / bags / expiry filters")


def build_search(trip: Trip, req: TripFlightSearch) -> FlightSearch:
    prefs = trip.flight_prefs
    try:
        return _search(trip, req, prefs)
    except ValidationError as exc:
        raise InvalidChange("Flight search rejected", [e["msg"] for e in exc.errors()]) from exc


def _search(trip: Trip, req: TripFlightSearch, prefs) -> FlightSearch:
    return FlightSearch(
        direction=req.direction,
        from_airport=req.from_airport,
        to_airport=req.to_airport,
        date=req.date or (trip.start_date if req.direction is Direction.OUTBOUND else trip.end_date),
        adults=trip.adults,
        children_ages=trip.children_ages,
        infants=trip.infants,
        cabin=req.cabin or prefs.cabin,
        max_stops=req.max_stops if req.max_stops is not None else prefs.max_stops,
        checked_bags=req.checked_bags if req.checked_bags is not None else prefs.checked_bags,
        sort=req.sort,
    )


def search_flights(
    trip: Trip, req: TripFlightSearch, provider: FlightProvider, snapshots: FlightSnapshots, now: datetime | None = None
) -> FlightSearchResult:
    search = build_search(trip, req)
    now = now or datetime.now(UTC)
    raw = provider.search(search)
    offers = filter_and_sort(raw, search, now)
    search_id = uuid4()
    snapshots.save(trip.id, search_id, search.direction, offers)
    return FlightSearchResult(
        search_id=search_id, search=search, offers=offers, searched_at=now, filtered_out=len(raw) - len(offers)
    )
