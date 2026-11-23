from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol


@dataclass(frozen=True)
class FlightSegment:
    origin: str
    destination: str
    departure: datetime
    arrival: datetime
    carrier: str
    flight_number: str


@dataclass(frozen=True)
class FlightOption:
    id: str
    segments: tuple[FlightSegment, ...]
    total_amount: float
    currency: str
    booking_url: str | None = None


@dataclass(frozen=True)
class Place:
    id: str
    name: str
    latitude: float
    longitude: float
    categories: tuple[str, ...] = ()


class FlightProvider(Protocol):
    def search(self, origin: str, destination: str, departure_date: date, travellers: int) -> list[FlightOption]: ...


class PlacesProvider(Protocol):
    def search(self, query: str, latitude: float, longitude: float) -> list[Place]: ...
