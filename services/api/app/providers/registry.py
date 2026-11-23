"""Pick provider adapters from settings. Live adapters are added here once D-02/D-03 are decided."""

from app.config import get_settings
from app.providers.base import PlacesProvider, RoutesProvider
from app.providers.mock_places import MockPlacesProvider
from app.providers.mock_routes import MockRoutesProvider

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
