"""Flight search API (FLIGHT-002). Offers are normalized snapshots with `expires_at` (A-24); no ticketing."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.errors import ERROR_RESPONSES
from app.api.routes.itinerary import TripDep
from app.db.flights import FlightSnapshots
from app.db.session import get_session
from app.orchestration.flights import FlightSearchResult, TripFlightSearch, search_flights
from app.providers import registry
from app.providers.base import FlightProvider

router = APIRouter(prefix="/v1/trips/{trip_id}/flights", tags=["flights"], responses=ERROR_RESPONSES)


def get_flight_provider() -> FlightProvider:
    return registry.flight_provider()


@router.post("/search", response_model=FlightSearchResult)
def search(
    trip: TripDep,
    payload: TripFlightSearch,
    provider: Annotated[FlightProvider, Depends(get_flight_provider)],
    session: Annotated[Session, Depends(get_session)],
) -> FlightSearchResult:
    """One direction. Passengers from the trip; cabin / max stops / bags default to the trip's flight prefs."""
    return search_flights(trip, payload, provider, FlightSnapshots(session))
