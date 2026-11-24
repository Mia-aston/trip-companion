"""Flight contracts (FLIGHT-001). Every flight adapter returns these; nothing else leaves an adapter.

Rules: docs/ARCHITECTURE.md#flight-search-m4 (A-23…A-25).
"""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, computed_field, model_validator

from app.domain.shared.models import Contract, Money, Provenance, TimeZoneName, UtcDatetime
from app.domain.trips.models import MAX_TRAVELLERS, CabinClass

AirportCode = Annotated[str, Field(pattern=r"^[A-Z]{3}$", examples=["CAI"], description="IATA airport/city code")]


class Direction(StrEnum):
    OUTBOUND = "outbound"
    RETURN = "return"


class SortBy(StrEnum):
    PRICE = "price"
    DURATION = "duration"


class FlightSegment(Contract):
    carrier: Annotated[str, Field(pattern=r"^[A-Z0-9]{2}$")]
    carrier_name: str
    flight_number: str = Field(min_length=1, max_length=10)
    origin: AirportCode
    destination: AirportCode
    origin_timezone: TimeZoneName
    destination_timezone: TimeZoneName
    departs_at: UtcDatetime
    arrives_at: UtcDatetime

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.arrives_at <= self.departs_at:
            raise ValueError("arrives_at must be after departs_at")
        return self


class Baggage(Contract):
    checked_bags: int = Field(ge=0, le=5, description="Checked bags included per passenger")
    carry_on: bool = True


class FlightOffer(Contract):
    id: str = Field(description="'<provider>:<offer_id>'")
    provider: str
    offer_id: str
    segments: Annotated[list[FlightSegment], Field(min_length=1, max_length=6)]
    cabin: CabinClass
    total: Money = Field(description="All passengers, in the offer currency")
    baggage: Baggage
    refundable: bool | None = None
    changeable: bool | None = None
    booking_url: str | None = Field(default=None, max_length=1000)
    expires_at: UtcDatetime
    provenance: Provenance

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.id != f"{self.provider}:{self.offer_id}":
            raise ValueError("id must be '<provider>:<offer_id>'")
        for a, b in zip(self.segments, self.segments[1:], strict=False):
            if a.destination != b.origin:
                raise ValueError("segments must connect")
            if b.departs_at < a.arrives_at:
                raise ValueError("segments must be chronological")
        if self.total.amount <= Decimal(0):
            raise ValueError("total must be positive")
        return self

    @computed_field
    @property
    def stops(self) -> int:
        return len(self.segments) - 1

    @computed_field
    @property
    def departs_at(self) -> datetime:
        return self.segments[0].departs_at

    @computed_field
    @property
    def arrives_at(self) -> datetime:
        return self.segments[-1].arrives_at

    @computed_field
    @property
    def duration_minutes(self) -> int:
        return int((self.arrives_at - self.departs_at).total_seconds() // 60)

    def expired(self, now: datetime) -> bool:
        return now >= self.expires_at


class FlightSearch(Contract):
    """One direction (A-25). Passengers and preferences normally come from the trip."""

    direction: Direction
    from_airport: AirportCode
    to_airport: AirportCode
    date: date
    adults: int = Field(default=1, ge=1, le=MAX_TRAVELLERS)
    children_ages: list[Annotated[int, Field(ge=2, le=17)]] = []
    infants: int = Field(default=0, ge=0)
    cabin: CabinClass = CabinClass.ECONOMY
    max_stops: int | None = Field(default=None, ge=0, le=3)
    checked_bags: int = Field(default=0, ge=0, le=3, description="Minimum checked bags included per passenger")
    sort: SortBy = SortBy.PRICE

    @model_validator(mode="after")
    def valid(self) -> Self:
        if self.from_airport == self.to_airport:
            raise ValueError("from and to airports must differ")
        if self.infants > self.adults:
            raise ValueError("at most one infant per adult")
        return self

    @property
    def passengers(self) -> int:
        return self.adults + len(self.children_ages) + self.infants


def filter_and_sort(offers: list[FlightOffer], search: FlightSearch, now: datetime) -> list[FlightOffer]:
    """Apply MVP filters (stops, bags, cabin, not expired) and sort. Pure."""
    kept = [
        o
        for o in offers
        if not o.expired(now)
        and o.cabin == search.cabin
        and (search.max_stops is None or o.stops <= search.max_stops)
        and o.baggage.checked_bags >= search.checked_bags
    ]
    if search.sort == SortBy.DURATION:
        return sorted(kept, key=lambda o: (o.duration_minutes, o.total.amount, o.id))
    return sorted(kept, key=lambda o: (o.total.amount, o.duration_minutes, o.id))
