from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from app.domain.places.models import Place, PlaceCategory
from app.domain.routing.models import RouteMatrix, TravelMode, Waypoint
from app.domain.shared.models import GeoPoint


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


class FlightProvider(Protocol):
    def search(self, origin: str, destination: str, departure_date: date, travellers: int) -> list[FlightOption]: ...


class PlacesProvider(Protocol):
    """Adapters return normalized `Place` objects only (PLACE-001)."""

    name: str

    def search(
        self, query: str, near: GeoPoint, *, radius_m: int = 25_000, categories: list[PlaceCategory] | None = None
    ) -> list[Place]: ...

    def details(self, place_id: str) -> Place | None: ...

    def resolve_city(self, city: str) -> Place | None: ...


class RoutesProvider(Protocol):
    """Adapters return a normalized `RouteMatrix` (ROUTE-001)."""

    name: str

    def matrix(self, waypoints: list[Waypoint], mode: TravelMode) -> RouteMatrix: ...
