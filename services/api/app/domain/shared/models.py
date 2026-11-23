"""Shared contracts (CORE-001). The only cross-module imports allowed besides a module's public service.

Pure types + validation. No I/O, no DB, no vendor code.
"""

from datetime import UTC, datetime, time
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Self
from zoneinfo import available_timezones

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    """Base for API/domain contracts: reject unknown fields so typos fail loudly."""

    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, json_schema_serialization_defaults_required=True
    )


CurrencyCode = Annotated[str, Field(pattern=r"^[A-Z]{3}$", examples=["GBP"], description="ISO-4217 code")]

_TIMEZONES = available_timezones()


def _check_tz(value: str) -> str:
    if value not in _TIMEZONES:
        raise ValueError(f"unknown IANA timezone: {value}")
    return value


TimeZoneName = Annotated[str, AfterValidator(_check_tz), Field(examples=["Africa/Cairo"])]


def _to_utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


UtcDatetime = Annotated[
    AwareDatetime,
    AfterValidator(_to_utc),
    Field(description="Offset required on input; normalized to and returned in UTC. Display in the stop's timezone."),
]


class Money(Contract):
    """Exact money. Serialized as a decimal string, never a float."""

    # One schema for requests and responses: amount is documented as a string both ways.
    model_config = ConfigDict(json_schema_mode_override="serialization")

    amount: Decimal = Field(
        max_digits=14, decimal_places=2, examples=["128.62"], json_schema_extra={"pattern": r"^-?\d{1,12}(\.\d{1,2})?$"}
    )
    currency: CurrencyCode


class ProvenanceSource(StrEnum):
    PROVIDER = "provider"
    USER = "user"
    AI = "ai"


class Provenance(Contract):
    """Where a user-visible fact came from and how fresh it is."""

    source: ProvenanceSource
    provider: str | None = None
    fetched_at: UtcDatetime | None = None
    expires_at: UtcDatetime | None = None

    @model_validator(mode="after")
    def provider_facts_are_timestamped(self) -> Self:
        if self.source is ProvenanceSource.PROVIDER and not (self.provider and self.fetched_at):
            raise ValueError("provider provenance needs provider and fetched_at")
        if self.expires_at and self.fetched_at and self.expires_at < self.fetched_at:
            raise ValueError("expires_at must be after fetched_at")
        return self


class TimeWindow(Contract):
    """Local wall-clock window within a day, e.g. 09:00-20:00."""

    start: time
    end: time

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self


class GeoPoint(Contract):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class Pace(StrEnum):
    RELAXED = "relaxed"
    BALANCED = "balanced"
    PACKED = "packed"


class MobilityNeeds(StrEnum):
    NONE = "none"
    LIMITED_WALKING = "limited_walking"
    WHEELCHAIR = "wheelchair"
    STROLLER = "stroller"


class DietaryRestriction(StrEnum):
    """Hard filter for food. Allergies trigger a 'verify with venue' warning in UI."""

    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    HALAL = "halal"
    KOSHER = "kosher"
    GLUTEN_FREE = "gluten_free"
    LACTOSE_FREE = "lactose_free"
    NUT_ALLERGY = "nut_allergy"
    SHELLFISH_ALLERGY = "shellfish_allergy"


class Interest(StrEnum):
    HISTORY = "history"
    FOOD = "food"
    PHOTO = "photo"
    NATURE = "nature"
    NIGHTLIFE = "nightlife"
    SHOPPING = "shopping"
    ART = "art"
    ADVENTURE = "adventure"


PriceLevel = Annotated[int, Field(ge=1, le=4, description="1 = budget … 4 = luxury")]
