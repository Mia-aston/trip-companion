"""Contract tests every provider adapter must pass (mock or real).

Add new adapters to the parametrize lists; real adapters should use recorded fixtures.
"""

from datetime import date
from itertools import pairwise

import pytest

from app.providers.base import FlightOption, FlightProvider, Place, PlacesProvider
from app.providers.mock_flights import MockFlightProvider
from app.providers.mock_places import MockPlacesProvider

FLIGHT_PROVIDERS: list[FlightProvider] = [MockFlightProvider()]
PLACES_PROVIDERS: list[PlacesProvider] = [MockPlacesProvider()]


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


@pytest.mark.parametrize("provider", PLACES_PROVIDERS, ids=lambda p: type(p).__name__)
class TestPlacesProviderContract:
    def test_returns_normalized_places(self, provider):
        places = provider.search("museum", 30.0444, 31.2357)
        assert places
        assert all(isinstance(p, Place) for p in places)

    def test_coordinates_are_valid(self, provider):
        for place in provider.search("museum", 30.0444, 31.2357):
            assert -90 <= place.latitude <= 90
            assert -180 <= place.longitude <= 180

    def test_ids_and_names_present(self, provider):
        places = provider.search("museum", 30.0444, 31.2357)
        assert all(p.id and p.name for p in places)
        assert len({p.id for p in places}) == len(places)

    def test_categories_are_tuple_of_strings(self, provider):
        for place in provider.search("museum", 30.0444, 31.2357):
            assert isinstance(place.categories, tuple)
            assert all(isinstance(c, str) for c in place.categories)
