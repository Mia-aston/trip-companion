"""Places contracts (PLACE-001). Every provider adapter returns these; nothing else leaves an adapter."""

from datetime import datetime, time, timedelta
from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, model_validator

from app.domain.shared.models import Contract, GeoPoint, PriceLevel, Provenance, TimeZoneName


class PlaceCategory(StrEnum):
    CITY = "city"
    LANDMARK = "landmark"
    MUSEUM = "museum"
    TEMPLE = "temple"
    ARCHAEOLOGICAL_SITE = "archaeological_site"
    MARKET = "market"
    PARK = "park"
    VIEWPOINT = "viewpoint"
    RESTAURANT = "restaurant"
    CAFE = "cafe"
    NATURE = "nature"
    NIGHTLIFE = "nightlife"
    SHOPPING = "shopping"
    ART = "art"
    ACTIVITY = "activity"


class OpeningPeriod(Contract):
    """One weekly opening interval in the place's local time. `close <= open` means it closes after midnight."""

    weekday: int = Field(ge=0, le=6, description="0 = Monday … 6 = Sunday (ISO weekday - 1)")
    open: time
    close: time


class Place(Contract):
    id: str = Field(description="Stable id: '<provider>:<provider_place_id>'")
    provider: str
    provider_place_id: str
    name: Annotated[str, Field(min_length=1, max_length=255)]
    city: str | None = Field(default=None, max_length=120)
    location: GeoPoint
    categories: list[PlaceCategory] = []
    opening_hours: list[OpeningPeriod] | None = Field(default=None, description="None = unknown; [] = never open")
    rating: float | None = Field(default=None, ge=0, le=5)
    rating_count: int | None = Field(default=None, ge=0)
    price_level: PriceLevel | None = None
    wheelchair_accessible: bool | None = None
    timezone: TimeZoneName
    typical_visit_minutes: int = Field(default=60, ge=5, le=600)
    provenance: Provenance

    @model_validator(mode="after")
    def id_matches_source(self) -> Self:
        if self.id != f"{self.provider}:{self.provider_place_id}":
            raise ValueError("id must be '<provider>:<provider_place_id>'")
        return self


def _intervals(period: OpeningPeriod, monday: datetime) -> tuple[datetime, datetime]:
    start = monday + timedelta(days=period.weekday, hours=period.open.hour, minutes=period.open.minute)
    end = monday + timedelta(days=period.weekday, hours=period.close.hour, minutes=period.close.minute)
    if end <= start:
        end += timedelta(days=1)
    return start, end


def open_intervals(place: Place, day_start: datetime) -> list[tuple[datetime, datetime]] | None:
    """Opening intervals (local naive datetimes) overlapping the local calendar day of `day_start`.

    Includes a previous-evening period that runs past midnight. None when hours are unknown.
    """
    if place.opening_hours is None:
        return None
    day = day_start.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    monday = day - timedelta(days=day.weekday())
    out = []
    for week in (monday - timedelta(days=7), monday):
        for p in place.opening_hours:
            start, end = _intervals(p, week)
            if start < day + timedelta(days=1) and end > day:
                out.append((start, end))
    return sorted(out)


def is_open_for(place: Place, start: datetime, minutes: int) -> bool | None:
    """True if the place is open for the whole [start, start+minutes) in local time. None when hours unknown."""
    intervals = open_intervals(place, start)
    if intervals is None:
        return None
    start = start.replace(tzinfo=None)
    end = start + timedelta(minutes=minutes)
    return any(a <= start and end <= b for a, b in intervals)
