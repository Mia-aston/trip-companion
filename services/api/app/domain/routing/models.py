"""Routing contracts (ROUTE-001). The itinerary engine consumes RouteMatrix, never provider routes."""

from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from app.domain.shared.models import Contract, GeoPoint, Provenance


class TravelMode(StrEnum):
    WALK = "walk"
    DRIVE = "drive"  # taxi / car; transit is NICE


class Waypoint(Contract):
    id: str
    location: GeoPoint


class RouteLeg(Contract):
    origin_id: str
    destination_id: str
    duration_s: int = Field(ge=0)
    distance_m: int = Field(ge=0)


class RouteMatrix(Contract):
    mode: TravelMode
    legs: list[RouteLeg]
    provenance: Provenance

    @model_validator(mode="after")
    def no_duplicate_pairs(self) -> Self:
        pairs = [(leg.origin_id, leg.destination_id) for leg in self.legs]
        if len(pairs) != len(set(pairs)):
            raise ValueError("duplicate origin/destination pair")
        return self

    def leg(self, origin_id: str, destination_id: str) -> RouteLeg | None:
        if origin_id == destination_id:
            return RouteLeg(origin_id=origin_id, destination_id=destination_id, duration_s=0, distance_m=0)
        return next((x for x in self.legs if x.origin_id == origin_id and x.destination_id == destination_id), None)

    def minutes(self, origin_id: str, destination_id: str) -> int | None:
        leg = self.leg(origin_id, destination_id)
        return None if leg is None else -(-leg.duration_s // 60)  # ceil
