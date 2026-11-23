"""Itinerary API (AI-002). Every change writes a new immutable plan version (A-19)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import Field
from sqlalchemy.orm import Session

from app.api.deps import Places, PlannerDep, Plans, Routes
from app.api.errors import ERROR_RESPONSES
from app.db.repositories import TripRepository
from app.db.session import get_session
from app.domain.itinerary.versions import PlanDiff, PlanVersion, compute_diff
from app.domain.shared.errors import NotFound
from app.domain.shared.models import Contract
from app.domain.trips.models import Trip
from app.orchestration.itinerary import generate_version

router = APIRouter(prefix="/v1/trips/{trip_id}/itinerary", tags=["itinerary"], responses=ERROR_RESPONSES)


class GenerateRequest(Contract):
    note: str = Field(default="", max_length=500, description="Stored as the version's reason")


def _trip(trip_id: UUID, session: Annotated[Session, Depends(get_session)]) -> Trip:
    trip = TripRepository(session).get(trip_id)
    if trip is None:
        raise NotFound(f"trip {trip_id} not found")
    return trip


TripDep = Annotated[Trip, Depends(_trip)]


@router.post("/generate", response_model=PlanVersion, status_code=status.HTTP_201_CREATED)
def generate(
    trip: TripDep,
    places: Places,
    routes: Routes,
    planner: PlannerDep,
    plans: Plans,
    payload: GenerateRequest | None = None,
) -> PlanVersion:
    """Plan (or re-plan) the whole trip. Locked and user-added items are kept; 422 with violations if invalid."""
    return generate_version(trip, places, routes, planner, plans, note=payload.note if payload else "")


@router.get("", response_model=PlanVersion)
def get_itinerary(trip: TripDep, plans: Plans, version: Annotated[int | None, Query(ge=1)] = None) -> PlanVersion:
    plan = plans.get(trip.id, version)
    if plan is None:
        raise NotFound("no itinerary yet" if version is None else f"version {version} not found")
    return plan


@router.get("/diff", response_model=PlanDiff)
def diff(
    trip: TripDep,
    plans: Plans,
    to: Annotated[int | None, Query(ge=1, description="Defaults to the latest version")] = None,
    from_: Annotated[int | None, Query(alias="from", ge=1, description="Defaults to to - 1")] = None,
) -> PlanDiff:
    target = plans.get(trip.id, to)
    if target is None:
        raise NotFound("no itinerary yet" if to is None else f"version {to} not found")
    base_version = from_ if from_ is not None else (target.version - 1 or None)
    base = plans.get(trip.id, base_version) if base_version else None
    if base_version and base is None:
        raise NotFound(f"version {base_version} not found")
    return compute_diff(base.days if base else None, target.days, base_version, target.version)
