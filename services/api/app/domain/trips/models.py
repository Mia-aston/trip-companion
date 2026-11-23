"""Trip Core contracts (CORE-001). Variables and tiers: docs/SCOPE.md#trip-input-variables.

Validation here covers single-payload invariants only. Rules that need stored state
(e.g. PATCH against the current trip) live in the trips service (CORE-003).
"""

from datetime import date, time, timedelta
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID, uuid4

from pydantic import AwareDatetime, Field, computed_field, model_validator

from app.domain.shared.models import (
    Contract,
    CurrencyCode,
    DietaryRestriction,
    Interest,
    MobilityNeeds,
    Money,
    Pace,
    PriceLevel,
    TimeWindow,
    TimeZoneName,
)

MAX_TRAVELLERS = 20
Name = Annotated[str, Field(min_length=1, max_length=120)]


def _unique(items: list) -> list:
    if len(items) != len(set(items)):
        raise ValueError("values must be unique")
    return items


# --- enums -----------------------------------------------------------------


class TripStatus(StrEnum):
    DRAFT = "draft"
    PLANNED = "planned"
    ACTIVE = "active"
    DONE = "done"


class BudgetScope(StrEnum):
    PER_TRIP = "per_trip"
    PER_PERSON = "per_person"


class CabinClass(StrEnum):
    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"


class MemberRole(StrEnum):
    OWNER = "owner"
    EDITOR = "editor"  # NEXT: sharing
    VIEWER = "viewer"  # NEXT: sharing


class Hardness(StrEnum):
    HARD = "hard"
    SOFT = "soft"


class ConstraintSource(StrEnum):
    USER = "user"
    BOOKING = "booking"
    SYSTEM = "system"


class BookingKind(StrEnum):
    FLIGHT = "flight"
    HOTEL = "hotel"
    ACTIVITY = "activity"
    TRANSPORT = "transport"


class BookingStatus(StrEnum):
    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


# --- value objects ---------------------------------------------------------


class Budget(Contract):
    total: Money
    scope: BudgetScope = BudgetScope.PER_TRIP


class FlightPrefs(Contract):
    max_stops: int | None = Field(default=None, ge=0, le=3, description="None = any")
    cabin: CabinClass = CabinClass.ECONOMY
    checked_bags: int = Field(default=1, ge=0, le=3)


DEFAULT_DAY_WINDOW = TimeWindow(start=time(9), end=time(20))


# --- stops (multi-city) ----------------------------------------------------


class StopCreate(Contract):
    city: Name
    nights: int = Field(ge=0, le=60)
    timezone: TimeZoneName | None = Field(default=None, description="Resolved from the place if omitted")
    accommodation_area: str | None = Field(default=None, max_length=200)


class Stop(StopCreate):
    id: UUID
    seq: int = Field(ge=0)
    arrive_on: date
    leave_on: date


# --- members ---------------------------------------------------------------


class MemberCreate(Contract):
    display_name: Annotated[str, Field(min_length=1, max_length=80)]
    role: MemberRole = MemberRole.OWNER
    currency_pref: CurrencyCode | None = None


class Member(MemberCreate):
    id: UUID
    user_id: UUID | None = None


# --- constraints (discriminated by kind) -----------------------------------


class MustDoCreate(Contract):
    kind: Literal["must_do"] = "must_do"
    hardness: Hardness = Hardness.HARD
    query: str | None = Field(default=None, max_length=200, examples=["Giza pyramids"])
    place_id: str | None = None
    on_date: date | None = None

    @model_validator(mode="after")
    def has_target(self) -> Self:
        if not (self.query or self.place_id):
            raise ValueError("must_do needs query or place_id")
        return self


class AvoidCreate(Contract):
    kind: Literal["avoid"] = "avoid"
    hardness: Hardness = Hardness.HARD
    query: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=60)

    @model_validator(mode="after")
    def has_target(self) -> Self:
        if not (self.query or self.category):
            raise ValueError("avoid needs query or category")
        return self


class TimeWindowConstraintCreate(Contract):
    """A fixed block the plan must respect, e.g. a meeting or a tour pickup."""

    kind: Literal["time_window"] = "time_window"
    hardness: Hardness = Hardness.HARD
    label: Name
    starts_at: AwareDatetime
    ends_at: AwareDatetime

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


ConstraintCreate = Annotated[
    MustDoCreate | AvoidCreate | TimeWindowConstraintCreate,
    Field(discriminator="kind"),
]


class _ConstraintState(Contract):
    id: UUID
    source: ConstraintSource = ConstraintSource.USER
    locked: bool = False


class MustDo(MustDoCreate, _ConstraintState):
    pass


class Avoid(AvoidCreate, _ConstraintState):
    pass


class TimeWindowConstraint(TimeWindowConstraintCreate, _ConstraintState):
    pass


Constraint = Annotated[MustDo | Avoid | TimeWindowConstraint, Field(discriminator="kind")]


# --- bookings (manual in MVP) ----------------------------------------------


class BookingCreate(Contract):
    kind: BookingKind
    title: Name
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    stop_seq: int | None = Field(default=None, ge=0, description="Which stop this belongs to")
    location_name: str | None = Field(default=None, max_length=200)
    reference: str | None = Field(default=None, max_length=120, description="Confirmation code")
    cost: Money | None = None
    status: BookingStatus = BookingStatus.CONFIRMED

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.ends_at < self.starts_at:
            raise ValueError("ends_at must be on or after starts_at")
        return self


class Booking(BookingCreate):
    id: UUID


# --- trip ------------------------------------------------------------------


class _TripPreferences(Contract):
    """Fields editable via PATCH and present on create."""

    title: Name
    base_currency: CurrencyCode
    settlement_currency: CurrencyCode | None = Field(default=None, description="Defaults to base_currency")
    budget: Budget | None = None
    pace: Pace = Pace.BALANCED
    day_window: TimeWindow = DEFAULT_DAY_WINDOW
    interests: Annotated[list[Interest], Field(max_length=8)] = []
    dietary: list[DietaryRestriction] = []
    mobility_needs: MobilityNeeds = MobilityNeeds.NONE
    price_level: PriceLevel = 2
    flight_prefs: FlightPrefs = FlightPrefs()

    @model_validator(mode="after")
    def unique_lists_and_currency_default(self) -> Self:
        _unique(self.interests)
        _unique(self.dietary)
        if self.settlement_currency is None:
            self.settlement_currency = self.base_currency
        return self


class _Travellers(Contract):
    adults: int = Field(default=1, ge=1, le=MAX_TRAVELLERS)
    children_ages: list[Annotated[int, Field(ge=2, le=17)]] = []
    infants: int = Field(default=0, ge=0, description="Under 2; lap infants, at most one per adult")

    @computed_field
    @property
    def travellers(self) -> int:
        return self.adults + len(self.children_ages) + self.infants

    @model_validator(mode="after")
    def party_is_valid(self) -> Self:
        if self.infants > self.adults:
            raise ValueError("at most one infant per adult")
        if self.travellers > MAX_TRAVELLERS:
            raise ValueError(f"at most {MAX_TRAVELLERS} travellers")
        return self


class TripCreate(_Travellers, _TripPreferences):
    origin: Name = Field(examples=["LON"])
    start_date: date
    end_date: date
    stops: Annotated[list[StopCreate], Field(min_length=1, max_length=20)]
    members: list[MemberCreate] = Field(default=[], description="Empty → the creator becomes the owner (CORE-003)")
    constraints: list[ConstraintCreate] = []
    bookings: list[BookingCreate] = []

    @model_validator(mode="after")
    def dates_and_stops_agree(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        nights = (self.end_date - self.start_date).days
        if sum(s.nights for s in self.stops) != nights:
            raise ValueError(f"stop nights must sum to the trip length ({nights} nights)")
        names = [m.display_name.casefold() for m in self.members]
        if len(names) != len(set(names)):
            raise ValueError("member display_name must be unique")
        for b in self.bookings:
            if b.stop_seq is not None and b.stop_seq >= len(self.stops):
                raise ValueError(f"booking '{b.title}' references unknown stop_seq {b.stop_seq}")
        return self


class TripUpdate(Contract):
    """PATCH body. Omitted fields are unchanged. Stops/members/constraints/bookings use sub-resources."""

    title: Name | None = None
    start_date: date | None = None
    end_date: date | None = None
    adults: int | None = Field(default=None, ge=1, le=MAX_TRAVELLERS)
    children_ages: list[Annotated[int, Field(ge=2, le=17)]] | None = None
    infants: int | None = Field(default=None, ge=0)
    base_currency: CurrencyCode | None = None
    settlement_currency: CurrencyCode | None = None
    budget: Budget | None = None
    pace: Pace | None = None
    day_window: TimeWindow | None = None
    interests: list[Interest] | None = None
    dietary: list[DietaryRestriction] | None = None
    mobility_needs: MobilityNeeds | None = None
    price_level: PriceLevel | None = None
    flight_prefs: FlightPrefs | None = None
    status: TripStatus | None = None


class Trip(_Travellers, _TripPreferences):
    id: UUID
    status: TripStatus = TripStatus.DRAFT
    origin: str
    start_date: date
    end_date: date
    settlement_currency: CurrencyCode  # always resolved on a stored trip
    stops: list[Stop]
    members: list[Member] = []
    constraints: list[Constraint] = []
    bookings: list[Booking] = []

    @classmethod
    def from_create(cls, payload: TripCreate) -> "Trip":
        """Build an unsaved Trip: assign ids and derive stop dates from nights."""
        data = payload.model_dump(exclude={"stops", "members", "constraints", "bookings", "travellers"})
        stops, day = [], payload.start_date
        for seq, s in enumerate(payload.stops):
            leave = day + timedelta(days=s.nights)
            stops.append(Stop(id=uuid4(), seq=seq, arrive_on=day, leave_on=leave, **s.model_dump()))
            day = leave
        constraint_types = {"must_do": MustDo, "avoid": Avoid, "time_window": TimeWindowConstraint}
        return cls(
            id=uuid4(),
            stops=stops,
            members=[Member(id=uuid4(), **m.model_dump()) for m in payload.members],
            constraints=[constraint_types[c.kind](id=uuid4(), **c.model_dump()) for c in payload.constraints],
            bookings=[Booking(id=uuid4(), **b.model_dump()) for b in payload.bookings],
            **data,
        )
