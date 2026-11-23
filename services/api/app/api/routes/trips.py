"""Trip Core API contract (CORE-001). Bodies/responses are frozen here; persistence lands in CORE-003.

Routes answering 501 are declared so OpenAPI (and generated TS types) describe the full M1 surface.
"""

from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.errors import ERROR_RESPONSES
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

router = APIRouter(prefix="/v1/trips", tags=["trips"], responses=ERROR_RESPONSES)


def _todo() -> NoReturn:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Not implemented yet (CORE-003)")


@router.post("", response_model=Trip, status_code=status.HTTP_201_CREATED)
def create_trip(payload: TripCreate) -> Trip:
    # Contract skeleton: validates and echoes an unsaved Trip. Persistence: CORE-003.
    return Trip.from_create(payload)


@router.get("/{trip_id}", response_model=Trip)
def get_trip(trip_id: UUID) -> Trip:
    _todo()


@router.patch("/{trip_id}", response_model=Trip)
def update_trip(trip_id: UUID, payload: TripUpdate) -> Trip:
    _todo()


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(trip_id: UUID) -> None:
    _todo()


@router.post("/{trip_id}/members", response_model=Member, status_code=status.HTTP_201_CREATED)
def add_member(trip_id: UUID, payload: MemberCreate) -> Member:
    _todo()


@router.delete("/{trip_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(trip_id: UUID, member_id: UUID) -> None:
    _todo()


@router.post("/{trip_id}/constraints", response_model=Constraint, status_code=status.HTTP_201_CREATED)
def add_constraint(trip_id: UUID, payload: ConstraintCreate) -> Constraint:
    _todo()


@router.delete("/{trip_id}/constraints/{constraint_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_constraint(trip_id: UUID, constraint_id: UUID) -> None:
    _todo()


@router.post("/{trip_id}/bookings", response_model=Booking, status_code=status.HTTP_201_CREATED)
def add_booking(trip_id: UUID, payload: BookingCreate) -> Booking:
    _todo()


@router.delete("/{trip_id}/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_booking(trip_id: UUID, booking_id: UUID) -> None:
    _todo()
