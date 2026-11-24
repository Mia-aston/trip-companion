"""Deterministic flight provider over sanitized route templates (tests/fixtures/flights/routes.json).

Prices: adult fare × adults + 75% per child + 10% per infant. Offers expire 30 minutes after the search (A-24).
"""

import json
from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from functools import cache
from pathlib import Path
from zoneinfo import ZoneInfo

from app.domain.flights.models import Baggage, FlightOffer, FlightSearch, FlightSegment
from app.domain.shared.models import Money, Provenance

FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "flights" / "routes.json"
OFFER_TTL = timedelta(minutes=30)
CHILD_SHARE, INFANT_SHARE = Decimal("0.75"), Decimal("0.10")


@cache
def _routes() -> dict[tuple[str, str], list[dict]]:
    data = json.loads(FIXTURE.read_text())
    return {(r["from"], r["to"]): r["options"] for r in data["routes"]}


def _at(day: date, hhmm: str, tz: str, offset: int = 0) -> datetime:
    return datetime.combine(day + timedelta(days=offset), time.fromisoformat(hhmm), ZoneInfo(tz))


class MockFlightProvider:
    name = "mock"

    def __init__(self, clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self.clock = clock

    def search(self, search: FlightSearch) -> list[FlightOffer]:
        now = self.clock()
        offers = []
        for option in _routes().get((search.from_airport, search.to_airport), []):
            fare = Decimal(option["adult_fare"])
            total = (
                fare * search.adults
                + fare * CHILD_SHARE * len(search.children_ages)
                + fare * INFANT_SHARE * search.infants
            )
            segments = [
                FlightSegment(
                    carrier=s["carrier"],
                    carrier_name=s["carrier_name"],
                    flight_number=s["flight_number"],
                    origin=s["origin"],
                    destination=s["destination"],
                    origin_timezone=s["origin_timezone"],
                    destination_timezone=s["destination_timezone"],
                    departs_at=_at(search.date, s["depart"], s["origin_timezone"], s.get("depart_day_offset", 0)),
                    arrives_at=_at(search.date, s["arrive"], s["destination_timezone"], s.get("arrive_day_offset", 0)),
                )
                for s in option["segments"]
            ]
            offer_id = (
                f"{option['key']}-{search.date:%Y%m%d}-{search.adults}a{len(search.children_ages)}c{search.infants}i"
            )
            offers.append(
                FlightOffer(
                    id=f"{self.name}:{offer_id}",
                    provider=self.name,
                    offer_id=offer_id,
                    segments=segments,
                    cabin=option["cabin"],
                    total=Money(amount=total.quantize(Decimal("0.01")), currency=option["currency"]),
                    baggage=Baggage(checked_bags=option["checked_bags"]),
                    refundable=option["refundable"],
                    changeable=option["changeable"],
                    booking_url=f"https://example.com/mock-booking/{offer_id}",
                    expires_at=now + OFFER_TTL,
                    provenance=Provenance(
                        source="provider", provider=self.name, fetched_at=now, expires_at=now + OFFER_TTL
                    ),
                )
            )
        return offers
