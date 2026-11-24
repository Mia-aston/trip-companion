from typing import Protocol

from app.domain.flights.models import FlightOffer, FlightSearch
from app.domain.places.models import Place, PlaceCategory
from app.domain.routing.models import RouteMatrix, TravelMode, Waypoint
from app.domain.shared.models import GeoPoint


class FlightProvider(Protocol):
    """Adapters return normalized `FlightOffer`s with `expires_at` (FLIGHT-001). Filtering/sorting is domain code."""

    name: str

    def search(self, search: FlightSearch) -> list[FlightOffer]: ...


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
