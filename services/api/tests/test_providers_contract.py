"""Contract tests every provider adapter must pass (mock or real).

Add new adapters to the parametrize lists; real adapters should use recorded fixtures.
"""

from datetime import date
from zoneinfo import ZoneInfo

import pytest

from app.domain.flights.models import FlightOffer, FlightSearch
from app.domain.places.models import Place, PlaceCategory
from app.domain.routing.geo import haversine_m
from app.domain.routing.models import RouteMatrix, TravelMode, Waypoint
from app.domain.shared.models import GeoPoint
from app.providers.base import FlightProvider, PlacesProvider, RoutesProvider
from app.providers.mock_flights import MockFlightProvider
from app.providers.mock_places import MockPlacesProvider
from app.providers.mock_routes import MockRoutesProvider

FLIGHT_PROVIDERS: list[FlightProvider] = [MockFlightProvider()]
PLACES_PROVIDERS: list[PlacesProvider] = [MockPlacesProvider()]
ROUTES_PROVIDERS: list[RoutesProvider] = [MockRoutesProvider()]


SEARCH = FlightSearch(direction="outbound", from_airport="LON", to_airport="CAI", date=date(2026, 10, 31), adults=2)


@pytest.mark.parametrize("provider", FLIGHT_PROVIDERS, ids=lambda p: type(p).__name__)
class TestFlightProviderContract:
    def test_returns_normalized_offers(self, provider):
        offers = provider.search(SEARCH)
        assert offers and all(isinstance(o, FlightOffer) for o in offers)

    def test_offer_ids_unique_and_prefixed(self, provider):
        offers = provider.search(SEARCH)
        assert len({o.id for o in offers}) == len(offers)
        assert all(o.id.startswith(f"{provider.name}:") for o in offers)

    def test_route_and_date_match_request(self, provider):
        for o in provider.search(SEARCH):
            first, last = o.segments[0], o.segments[-1]
            assert first.departs_at.astimezone(ZoneInfo(first.origin_timezone)).date() == SEARCH.date
            assert first.origin in {"LHR", "LGW", "STN", "LTN", "LCY", "LON"}
            assert last.destination == "CAI"

    def test_offers_expire_and_carry_provenance(self, provider):
        for o in provider.search(SEARCH):
            assert o.provenance.source == "provider" and o.provenance.fetched_at is not None
            assert o.expires_at > o.provenance.fetched_at

    def test_price_scales_with_passengers(self, provider):
        one = {
            o.offer_id.split("-")[0]: o.total.amount
            for o in provider.search(FlightSearch.model_validate({**SEARCH.model_dump(), "adults": 1}))
        }
        two = {o.offer_id.split("-")[0]: o.total.amount for o in provider.search(SEARCH)}
        assert all(two[k] > one[k] for k in one)

    def test_unknown_route_is_empty(self, provider):
        assert provider.search(FlightSearch.model_validate({**SEARCH.model_dump(), "to_airport": "SYD"})) == []


CAIRO = GeoPoint(lat=30.0444, lon=31.2357)


@pytest.mark.parametrize("provider", PLACES_PROVIDERS, ids=lambda p: type(p).__name__)
class TestPlacesProviderContract:
    def test_returns_normalized_places(self, provider):
        places = provider.search("museum", CAIRO)
        assert places
        assert all(isinstance(p, Place) for p in places)

    def test_results_are_within_radius_and_nearest_first(self, provider):
        places = provider.search("", CAIRO, radius_m=10_000)
        distances = [haversine_m(CAIRO, p.location) for p in places]
        assert all(d <= 10_000 for d in distances)
        assert distances == sorted(distances)

    def test_ids_unique_and_prefixed_by_provider(self, provider):
        places = provider.search("", CAIRO)
        assert len({p.id for p in places}) == len(places)
        assert all(p.id.startswith(f"{p.provider}:") for p in places)

    def test_provider_provenance_is_timestamped(self, provider):
        for place in provider.search("", CAIRO):
            assert place.provenance.source == "provider" and place.provenance.fetched_at is not None

    def test_category_filter(self, provider):
        places = provider.search("", CAIRO, categories=[PlaceCategory.MUSEUM])
        assert places and all(PlaceCategory.MUSEUM in p.categories for p in places)

    def test_details_round_trip_and_unknown(self, provider):
        place = provider.search("museum", CAIRO)[0]
        assert provider.details(place.id) == place
        assert provider.details(f"{provider.name}:does-not-exist") is None

    def test_resolve_city(self, provider):
        city = provider.resolve_city("cairo")
        assert city is not None and PlaceCategory.CITY in city.categories
        assert provider.resolve_city("Atlantis") is None


@pytest.mark.parametrize("provider", ROUTES_PROVIDERS, ids=lambda p: type(p).__name__)
class TestRoutesProviderContract:
    POINTS = [
        Waypoint(id="museum", location=GeoPoint(lat=30.0478, lon=31.2336)),
        Waypoint(id="khan", location=GeoPoint(lat=30.0477, lon=31.2623)),
        Waypoint(id="pyramids", location=GeoPoint(lat=29.9792, lon=31.1342)),
    ]

    @pytest.mark.parametrize("mode", list(TravelMode))
    def test_full_matrix_without_self_legs(self, provider, mode):
        matrix = provider.matrix(self.POINTS, mode)
        assert isinstance(matrix, RouteMatrix) and matrix.mode == mode
        assert len(matrix.legs) == 6
        assert matrix.minutes("museum", "museum") == 0

    def test_farther_is_longer(self, provider):
        matrix = provider.matrix(self.POINTS, TravelMode.DRIVE)
        assert matrix.minutes("museum", "pyramids") > matrix.minutes("museum", "khan")

    def test_walking_slower_than_driving_over_distance(self, provider):
        walk = provider.matrix(self.POINTS, TravelMode.WALK).minutes("museum", "pyramids")
        drive = provider.matrix(self.POINTS, TravelMode.DRIVE).minutes("museum", "pyramids")
        assert walk > drive

    def test_unknown_pair_is_none(self, provider):
        assert provider.matrix(self.POINTS, TravelMode.WALK).leg("museum", "nowhere") is None
