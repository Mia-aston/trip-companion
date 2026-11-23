from datetime import date
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


class Pace(StrEnum):
    RELAXED = "relaxed"
    BALANCED = "balanced"
    PACKED = "packed"


class TripCreate(BaseModel):
    origin: str = Field(min_length=2)
    destination: str = Field(min_length=2)
    start_date: date
    end_date: date
    travellers: int = Field(default=1, ge=1, le=20)
    interests: list[str] = Field(default_factory=list)
    pace: Pace = Pace.BALANCED

    @model_validator(mode="after")
    def dates_are_valid(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class Trip(TripCreate):
    id: UUID

    @classmethod
    def from_create(cls, payload: TripCreate) -> "Trip":
        return cls(id=uuid4(), **payload.model_dump())
