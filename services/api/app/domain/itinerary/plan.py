"""Itinerary plan contracts (AI-001) and materialisation into canonical plan days. Pure.

- `ProposedPlan`: what a Planner returns — local wall-clock times, no ids (LLM-friendly schema).
- `PlanDay` / `PlanItem`: canonical, UTC instants + stable `item_key`s; what is validated, stored and diffed.
Rules: docs/ARCHITECTURE.md#itinerary-engine-m3.
"""

from datetime import date, datetime, time
from enum import StrEnum
from typing import Self
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5
from zoneinfo import ZoneInfo

from pydantic import Field, model_validator

from app.domain.shared.models import Contract, UtcDatetime
from app.domain.trips.models import BookingKind, BookingStatus, Trip


class ItemKind(StrEnum):
    PLACE = "place"
    BOOKING = "booking"
    TRANSFER = "transfer"
    MEAL = "meal"
    CUSTOM = "custom"
    FREE = "free"


class ItemSource(StrEnum):
    PLANNER = "planner"
    USER = "user"
    BOOKING = "booking"


# Bookings that occupy time on a day. Hotels are day context (where you sleep), not itinerary items.
TIMED_BOOKINGS = (BookingKind.FLIGHT, BookingKind.TRANSPORT, BookingKind.ACTIVITY)


# --- planner output (AI-001) -------------------------------------------------


class ProposedItem(Contract):
    kind: ItemKind
    title: str = Field(min_length=1, max_length=200)
    place_id: str | None = None
    start: time
    end: time
    why: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def valid(self) -> Self:
        if self.end <= self.start:
            raise ValueError("end must be after start")
        if self.kind is ItemKind.PLACE and not self.place_id:
            raise ValueError("place items need place_id")
        if self.kind is ItemKind.BOOKING:
            raise ValueError("planners never propose booking items")
        return self


class ProposedDay(Contract):
    date: date
    items: list[ProposedItem]


class ProposedPlan(Contract):
    days: list[ProposedDay]
    explanation: str = Field(default="", max_length=2000)


# --- canonical plan -------------------------------------------------------------


class PlanItem(Contract):
    item_key: UUID
    kind: ItemKind
    title: str
    place_id: str | None = None
    booking_id: UUID | None = None
    starts_at: UtcDatetime
    ends_at: UtcDatetime
    locked: bool = False
    weather_sensitive: bool = False
    source: ItemSource
    why: str = ""

    def same_content(self, other: "PlanItem") -> bool:
        """Equal apart from `why` — used for V5/V6 and diffs."""
        return self.model_dump(exclude={"why"}) == other.model_dump(exclude={"why"})


class PlanDay(Contract):
    date: date
    stop_seq: int
    timezone: str
    items: list[PlanItem]

    def local(self, dt: datetime) -> datetime:
        return dt.astimezone(ZoneInfo(self.timezone)).replace(tzinfo=None)


def booking_item_key(trip: Trip, booking_id: UUID) -> UUID:
    """Booking items get a deterministic key so they are identical across versions."""
    return uuid5(NAMESPACE_URL, f"trip:{trip.id}:booking:{booking_id}")


def booking_items(trip: Trip, day: date, tz: ZoneInfo) -> list[PlanItem]:
    out = []
    for b in trip.bookings:
        if b.kind not in TIMED_BOOKINGS or b.status is BookingStatus.CANCELLED:
            continue
        if b.starts_at.astimezone(tz).date() != day:
            continue
        out.append(
            PlanItem(
                item_key=booking_item_key(trip, b.id),
                kind=ItemKind.BOOKING,
                title=b.title,
                booking_id=b.id,
                starts_at=b.starts_at,
                ends_at=b.ends_at,
                locked=True,
                source=ItemSource.BOOKING,
            )
        )
    return out


def materialize(
    trip: Trip,
    proposed: ProposedPlan,
    days: list[tuple[date, int, str]],
    keep: dict[date, list[PlanItem]] | None = None,
) -> list[PlanDay]:
    """Build canonical days: booking items + items kept from a previous version + proposed items.

    `days` = (date, stop_seq, timezone) for every trip date. `keep` = non-booking items to carry over per date.
    Weather-sensitive flag is set on proposed items whose title matches a weather-sensitive booking (none in MVP).
    """
    by_date = {d.date: d for d in proposed.days}
    out = []
    for day, stop_seq, tz_name in days:
        tz = ZoneInfo(tz_name)
        items = booking_items(trip, day, tz) + list((keep or {}).get(day, []))
        for p in by_date.get(day, ProposedDay(date=day, items=[])).items:
            items.append(
                PlanItem(
                    item_key=uuid4(),
                    kind=p.kind,
                    title=p.title,
                    place_id=p.place_id,
                    starts_at=datetime.combine(day, p.start, tz),
                    ends_at=datetime.combine(day, p.end, tz),
                    source=ItemSource.PLANNER,
                    why=p.why,
                )
            )
        items.sort(key=lambda i: (i.starts_at, i.ends_at, str(i.item_key)))
        out.append(PlanDay(date=day, stop_seq=stop_seq, timezone=tz_name, items=items))
    return out
