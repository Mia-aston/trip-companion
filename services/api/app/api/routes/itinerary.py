"""Itinerary API (AI-002). Every change writes a new immutable plan version (A-19)."""

from datetime import date, time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import Field
from sqlalchemy.orm import Session

from app.api.deps import Places, PlannerDep, Plans, Routes
from app.api.errors import ERROR_RESPONSES
from app.db.repositories import TripRepository
from app.db.session import get_session
from app.domain.itinerary import edits
from app.domain.itinerary.versions import PlanDiff, PlanVersion, compute_diff
from app.domain.shared.errors import NotFound
from app.domain.shared.models import Contract, Pace
from app.domain.trips.models import Trip
from app.orchestration.itinerary import apply_user_edit, generate_version, regenerate_day

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


# --- one-day regenerate (ITIN-003, A-20) --------------------------------------------


class RegenerateScope(Contract):
    date: date


class RegenerateRequest(Contract):
    scope: RegenerateScope
    remove_item_keys: list[UUID] = Field(default=[], description="User items to drop, e.g. a custom 'Aswan day trip'")
    exclude_place_ids: list[str] = []
    stay_within_m: int | None = Field(
        default=None, ge=200, le=50_000, description="Only places this close to the stop base"
    )
    pace: Pace | None = None
    note: str = Field(default="", max_length=500, description="Stored as the version's reason; not interpreted")


@router.post("/regenerate", response_model=PlanVersion, status_code=status.HTTP_201_CREATED)
def regenerate(
    trip: TripDep, places: Places, routes: Routes, planner: PlannerDep, plans: Plans, payload: RegenerateRequest
) -> PlanVersion:
    """Re-plan one day. Bookings, locked items, kept user items and all other days stay identical."""
    return regenerate_day(
        trip,
        places,
        routes,
        planner,
        plans,
        on=payload.scope.date,
        remove_item_keys=payload.remove_item_keys,
        exclude_place_ids=payload.exclude_place_ids,
        stay_within_m=payload.stay_within_m,
        pace=payload.pace,
        note=payload.note,
    )


# --- item edits (each writes a new version) -------------------------------------------


class AddItem(Contract):
    date: date
    title: str = Field(min_length=1, max_length=200)
    start: time
    end: time
    place_id: str | None = Field(default=None, description="Set to make it a place visit; otherwise a custom item")


class EditItem(Contract):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    start: time | None = None
    end: time | None = None


class LockItem(Contract):
    locked: bool


@router.post("/items", response_model=PlanVersion, status_code=status.HTTP_201_CREATED)
def add_item(trip: TripDep, places: Places, routes: Routes, plans: Plans, payload: AddItem) -> PlanVersion:
    """Add your own item; overlapping unlocked planner items on that day are dropped."""
    return apply_user_edit(
        trip,
        places,
        routes,
        plans,
        lambda days: edits.add_item(days, payload.date, payload.title, payload.start, payload.end, payload.place_id),
        lambda item: f"Added '{item.title}'",
    )


@router.patch("/items/{item_key}", response_model=PlanVersion)
def edit_item(
    trip: TripDep, places: Places, routes: Routes, plans: Plans, item_key: UUID, payload: EditItem
) -> PlanVersion:
    return apply_user_edit(
        trip,
        places,
        routes,
        plans,
        lambda days: edits.edit_item(days, item_key, title=payload.title, start=payload.start, end=payload.end),
        lambda item: f"Edited '{item.title}'",
    )


@router.delete("/items/{item_key}", response_model=PlanVersion)
def delete_item(trip: TripDep, places: Places, routes: Routes, plans: Plans, item_key: UUID) -> PlanVersion:
    """Remove an unlocked, non-booking item. Returns the new version."""
    return apply_user_edit(
        trip,
        places,
        routes,
        plans,
        lambda days: edits.delete_item(days, item_key),
        lambda item: f"Removed '{item.title}'",
    )


@router.post("/items/{item_key}/lock", response_model=PlanVersion)
def lock_item(
    trip: TripDep, places: Places, routes: Routes, plans: Plans, item_key: UUID, payload: LockItem
) -> PlanVersion:
    return apply_user_edit(
        trip,
        places,
        routes,
        plans,
        lambda days: edits.set_lock(days, item_key, payload.locked),
        lambda item: f"{'Locked' if payload.locked else 'Unlocked'} '{item.title}'",
    )
