"""Contract tests every provider adapter must pass (mock or real).

Add new adapters to the parametrize lists; real adapters should use recorded fixtures.
"""

from datetime import date
from itertools import pairwise

import pytest

from app.domain.places.models import Place, PlaceCategory
from app.domain.routing.geo import haversine_m
from app.domain.routing.models import RouteMatrix, TravelMode, Waypoint
from app.domain.shared.models import GeoPoint
from app.providers.base import FlightOption, FlightProvider, PlacesProvider, RoutesProvider
from app.providers.mock_flights import MockFlightProvider
from app.providers.mock_places import MockPlacesProvider
from app.providers.mock_routes import MockRoutesProvider

FLIGHT_PROVIDERS: list[FlightProvider] = [MockFlightProvider()]
PLACES_PROVIDERS: list[PlacesProvider] = [MockPlacesProvider()]
ROUTES_PROVIDERS: list[RoutesProvider] = [MockRoutesProvider()]


@pytest.mark.parametrize("provider", FLIGHT_PROVIDERS, ids=lambda p: type(p).__name__)
class TestFlightProviderContract:
    def search(self, provider: FlightProvider, travellers: int = 2) -> list[FlightOption]:
        return provider.search("LHR", "CAI", date(2027, 3, 14), travellers)

    def test_returns_normalized_options(self, provider):
        options = self.search(provider)
        assert options, "provider should return at least one option for a valid route"
        assert all(isinstance(o, FlightOption) for o in options)

    def test_option_ids_are_unique(self, provider):
        ids = [o.id for o in self.search(provider)]
        assert len(ids) == len(set(ids))

    def test_itinerary_matches_requested_route(self, provider):
        for option in self.search(provider):
            assert option.segments
            assert option.segments[0].origin == "LHR"
            assert option.segments[-1].destination == "CAI"
            assert option.segments[0].departure.date() == date(2027, 3, 14)

    def test_segments_are_chronological_and_connected(self, provider):
        for option in self.search(provider):
            for seg in option.segments:
                assert seg.arrival > seg.departure
            for prev, nxt in pairwise(option.segments):
                assert prev.destination == nxt.origin
                assert nxt.departure >= prev.arrival

    def test_price_is_positive_iso_currency(self, provider):
        for option in self.search(provider):
            assert option.total_amount > 0
            assert len(option.currency) == 3 and option.currency.isupper()

    def test_price_covers_all_travellers(self, provider):
        one = min(o.total_amount for o in self.search(provider, travellers=1))
        three = min(o.total_amount for o in self.search(provider, travellers=3))
        assert three >= one


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
