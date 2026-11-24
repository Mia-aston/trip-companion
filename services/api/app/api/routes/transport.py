"""Transport selection API (FLIGHT-004). Ticketing stays on the provider's site (A-23)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Places, Routes
from app.api.errors import ERROR_RESPONSES
from app.api.routes.itinerary import TripDep
from app.db.flights import FlightSnapshots
from app.db.repositories import TripRepository
from app.db.session import get_session
from app.orchestration.transport import SelectOffer, SelectResult, select_offer

router = APIRouter(prefix="/v1/trips/{trip_id}/transport", tags=["flights"], responses=ERROR_RESPONSES)


@router.post("/select", response_model=SelectResult)
def select(
    trip: TripDep,
    payload: SelectOffer,
    places: Places,
    routes: Routes,
    session: Annotated[Session, Depends(get_session)],
) -> SelectResult:
    """Turn an unexpired offer into a tentative flight booking (replaces the same direction). 409 if expired."""
    return select_offer(trip, payload.offer_id, TripRepository(session), FlightSnapshots(session), places, routes)
