"""Pick provider adapters from settings. Live adapters are added here once D-02/D-03 are decided."""

from app.config import get_settings
from app.providers.base import FlightProvider, PlacesProvider, RoutesProvider
from app.providers.mock_flights import MockFlightProvider
from app.providers.mock_places import MockPlacesProvider
from app.providers.mock_routes import MockRoutesProvider

_FLIGHTS = {"mock": MockFlightProvider}
_PLACES = {"mock": MockPlacesProvider}
_ROUTES = {"mock": MockRoutesProvider}


def places_provider() -> PlacesProvider:
    name = get_settings().places_provider
    if name not in _PLACES:
        raise RuntimeError(f"unknown PLACES_PROVIDER '{name}' (available: {', '.join(_PLACES)})")
    return _PLACES[name]()


def routes_provider() -> RoutesProvider:
    name = get_settings().routes_provider
    if name not in _ROUTES:
        raise RuntimeError(f"unknown ROUTES_PROVIDER '{name}' (available: {', '.join(_ROUTES)})")
    return _ROUTES[name]()


def flight_provider() -> FlightProvider:
    name = get_settings().flight_provider
    if name not in _FLIGHTS:
        raise RuntimeError(
            f"unknown FLIGHT_PROVIDER '{name}' (available: {', '.join(_FLIGHTS)}; live adapter waits for D-03)"
        )
    return _FLIGHTS[name]()
