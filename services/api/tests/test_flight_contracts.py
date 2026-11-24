"""FLIGHT-001: flight contracts, filters/sort, mock pricing and expiry."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.domain.flights.models import FlightOffer, FlightSearch, filter_and_sort
from app.providers.mock_flights import MockFlightProvider

NOW = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
SEARCH = FlightSearch(direction="outbound", from_airport="LON", to_airport="CAI", date=date(2026, 10, 31), adults=2)


def _search(**changes) -> FlightSearch:
    return FlightSearch.model_validate({**SEARCH.model_dump(), **changes})


def _offers(**changes):
    return MockFlightProvider(clock=lambda: NOW).search(_search(**changes))


def _by_key(offers):
    return {o.offer_id.split("-")[0]: o for o in offers}


def test_egypt_arrival_flight_matches_fixture():
    nm778 = _by_key(_offers())["nm778"]
    assert nm778.arrives_at.astimezone(ZoneInfo("Africa/Cairo")).strftime("%Y-%m-%d %H:%M") == "2026-10-31 23:30"
    assert (nm778.stops, nm778.duration_minutes) == (0, 300)  # 16:30 London (UTC+0) → 23:30 Cairo (UTC+2)


def test_one_stop_offer_is_connected():
    bm = _by_key(_offers())["bm1980"]
    assert bm.stops == 1 and bm.segments[0].destination == bm.segments[1].origin == "IST"


def test_overnight_return_arrives_next_day():
    back = FlightSearch(direction="return", from_airport="LXR", to_airport="LON", date=date(2026, 11, 6), adults=2)
    nm315 = _by_key(MockFlightProvider(clock=lambda: NOW).search(back))["nm315"]
    assert nm315.departs_at == datetime(2026, 11, 6, 20, 30, tzinfo=UTC)  # 22:30 Luxor
    assert nm315.arrives_at.date() == date(2026, 11, 7)


def test_pricing_children_and_infants():
    base = _by_key(_offers(adults=1))["nm778"].total.amount
    family = _by_key(_offers(adults=2, children_ages=[8], infants=1))["nm778"].total.amount
    assert base == 290 and family == 290 * 2 + 290 * 0.75 + 290 * 0.10


def test_offers_expire_after_30_minutes():
    offer = _offers()[0]
    assert offer.expires_at == NOW + timedelta(minutes=30)
    assert not offer.expired(NOW + timedelta(minutes=29)) and offer.expired(NOW + timedelta(minutes=30))


def test_filter_and_sort():
    offers = _offers()
    cheapest = filter_and_sort(offers, SEARCH, NOW)
    assert [o.offer_id.split("-")[0] for o in cheapest] == ["bm1980", "nm778", "nm780"]  # business filtered by cabin
    direct = filter_and_sort(offers, _search(max_stops=0), NOW)
    assert all(o.stops == 0 for o in direct) and len(direct) == 2
    with_bag = filter_and_sort(offers, _search(checked_bags=1), NOW)
    assert "bm1980" not in [o.offer_id.split("-")[0] for o in with_bag]
    fastest = filter_and_sort(offers, _search(sort="duration"), NOW)
    assert fastest[-1].offer_id.startswith("bm1980")
    business = filter_and_sort(offers, _search(cabin="business"), NOW)
    assert [o.offer_id.split("-")[0] for o in business] == ["nm780j"]
    assert filter_and_sort(offers, SEARCH, NOW + timedelta(hours=1)) == []  # all expired


@pytest.mark.parametrize(
    "bad",
    [
        {"from_airport": "lon"},
        {"from_airport": "CAI"},
        {"adults": 0},
        {"adults": 1, "infants": 2},
        {"max_stops": 4},
        {"direction": "sideways"},
    ],
    ids=["lowercase-iata", "same-airports", "no-adults", "infants-exceed", "too-many-stops", "bad-direction"],
)
def test_search_rejects(bad):
    with pytest.raises(ValidationError):
        FlightSearch.model_validate({**SEARCH.model_dump(), **bad})


def _offer_dict(**changes):
    return {
        **_offers()[0].model_dump(mode="json", exclude={"stops", "departs_at", "arrives_at", "duration_minutes"}),
        **changes,
    }


def test_offer_rejects_disconnected_or_inconsistent():
    bm = _by_key(_offers())["bm1980"].model_dump(
        mode="json", exclude={"stops", "departs_at", "arrives_at", "duration_minutes"}
    )
    bm["segments"][1]["origin"] = "ATH"
    with pytest.raises(ValidationError):
        FlightOffer.model_validate(bm)
    with pytest.raises(ValidationError):
        FlightOffer.model_validate(_offer_dict(id="mock:other"))
    with pytest.raises(ValidationError):
        FlightOffer.model_validate(_offer_dict(total={"amount": "0.00", "currency": "GBP"}))
