from fastapi import APIRouter

from app.domain.trips.models import Trip, TripCreate

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("", response_model=Trip)
def create_trip(payload: TripCreate) -> Trip:
    # Persistence is intentionally deferred; this is the contract skeleton.
    return Trip.from_create(payload)
