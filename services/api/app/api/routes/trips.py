"""Trip Core API (CORE-003). Thin controllers: validate → domain rules → repository. Contract: docs/API_CONTRACTS.md."""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Response, status
from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from app.api.deps import Places, Routes
from app.api.errors import ERROR_RESPONSES
from app.db.repositories import TripRepository
from app.db.session import get_session
from app.domain.itinerary.days import TripDayCandidates
from app.domain.shared.errors import NotFound
from app.domain.trips import rules
from app.domain.trips.models import (
    Booking,
    BookingCreate,
    Constraint,
    ConstraintCreate,
    Member,
    MemberCreate,
    Trip,
    TripCreate,
    TripUpdate,
)
from app.orchestration.day_candidates import build_day_candidates

router = APIRouter(prefix="/v1/trips", tags=["trips"], responses=ERROR_RESPONSES)
_CONSTRAINT = TypeAdapter(Constraint)


def get_repo(session: Annotated[Session, Depends(get_session)]) -> TripRepository:
    return TripRepository(session)


Repo = Annotated[TripRepository, Depends(get_repo)]
NO_CONTENT = {"status_code": status.HTTP_204_NO_CONTENT, "response_class": Response}


def _load(repo: TripRepository, trip_id: UUID) -> Trip:
    trip = repo.get(trip_id)
    if trip is None:
        raise NotFound(f"trip {trip_id} not found")
    return trip


def _gone(found: bool, what: str) -> None:
    if not found:
        raise NotFound(f"{what} not found")


@router.post("", response_model=Trip, status_code=status.HTTP_201_CREATED)
def create_trip(payload: TripCreate, repo: Repo) -> Trip:
    # D-01: no auth yet → owner_id stays NULL (A-12).
    return repo.add(payload)


@router.get("/{trip_id}", response_model=Trip)
def get_trip(trip_id: UUID, repo: Repo) -> Trip:
    return _load(repo, trip_id)


@router.patch("/{trip_id}", response_model=Trip)
def update_trip(trip_id: UUID, payload: TripUpdate, repo: Repo) -> Trip:
    repo.save(rules.apply_update(_load(repo, trip_id), payload))
    return _load(repo, trip_id)


@router.delete("/{trip_id}", **NO_CONTENT)
def delete_trip(trip_id: UUID, repo: Repo) -> None:
    _gone(repo.delete(trip_id), f"trip {trip_id}")


@router.post("/{trip_id}/members", response_model=Member, status_code=status.HTTP_201_CREATED)
def add_member(trip_id: UUID, payload: MemberCreate, repo: Repo) -> Member:
    rules.check_new_member(_load(repo, trip_id), payload)
    return repo.add_member(trip_id, Member(id=uuid4(), **payload.model_dump()))


@router.delete("/{trip_id}/members/{member_id}", **NO_CONTENT)
def remove_member(trip_id: UUID, member_id: UUID, repo: Repo) -> None:
    _load(repo, trip_id)
    _gone(repo.remove_member(trip_id, member_id), f"member {member_id}")


@router.post("/{trip_id}/constraints", response_model=Constraint, status_code=status.HTTP_201_CREATED)
def add_constraint(trip_id: UUID, payload: ConstraintCreate, repo: Repo) -> Constraint:
    _load(repo, trip_id)
    constraint = _CONSTRAINT.validate_python({**payload.model_dump(), "id": uuid4()})
    return repo.add_constraint(trip_id, constraint)


@router.delete("/{trip_id}/constraints/{constraint_id}", **NO_CONTENT)
def remove_constraint(trip_id: UUID, constraint_id: UUID, repo: Repo) -> None:
    _load(repo, trip_id)
    _gone(repo.remove_constraint(trip_id, constraint_id), f"constraint {constraint_id}")


@router.post("/{trip_id}/bookings", response_model=Booking, status_code=status.HTTP_201_CREATED)
def add_booking(trip_id: UUID, payload: BookingCreate, repo: Repo) -> Booking:
    rules.check_new_booking(_load(repo, trip_id), payload)
    return repo.add_booking(trip_id, Booking(id=uuid4(), **payload.model_dump()))


@router.delete("/{trip_id}/bookings/{booking_id}", **NO_CONTENT)
def remove_booking(trip_id: UUID, booking_id: UUID, repo: Repo) -> None:
    _load(repo, trip_id)
    _gone(repo.remove_booking(trip_id, booking_id), f"booking {booking_id}")


@router.get("/{trip_id}/day-candidates", response_model=TripDayCandidates)
def day_candidates(trip_id: UUID, repo: Repo, places: Places, routes: Routes) -> TripDayCandidates:
    """Per day: available window, capacity and ranked feasible places (ITIN-001). Read-only; nothing is scheduled."""
    return build_day_candidates(_load(repo, trip_id), places, routes)
