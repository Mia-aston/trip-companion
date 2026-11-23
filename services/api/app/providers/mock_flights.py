from datetime import date, datetime, time, timedelta

from app.providers.base import FlightOption, FlightSegment


class MockFlightProvider:
    def search(self, origin: str, destination: str, departure_date: date, travellers: int) -> list[FlightOption]:
        departure = datetime.combine(departure_date, time(hour=9))
        arrival = departure + timedelta(hours=4)
        return [
            FlightOption(
                id="mock-direct-1",
                segments=(
                    FlightSegment(
                        origin=origin,
                        destination=destination,
                        departure=departure,
                        arrival=arrival,
                        carrier="MOCK",
                        flight_number="MOCK101",
                    ),
                ),
                total_amount=150.0 * travellers,
                currency="GBP",
                booking_url=None,
            )
        ]
