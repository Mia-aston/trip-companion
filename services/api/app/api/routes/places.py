"""Places API (PLACE-003). Returns normalized, cached `Place` objects with provenance."""

from typing import Annotated

from fastapi import APIRouter, Path
from pydantic import Field

from app.api.deps import Places
from app.api.errors import ERROR_RESPONSES
from app.domain.places.models import Place, PlaceCategory
from app.domain.shared.errors import NotFound
from app.domain.shared.models import Contract, GeoPoint

router = APIRouter(prefix="/v1/places", tags=["places"], responses=ERROR_RESPONSES)


class PlaceSearch(Contract):
    query: str = Field(default="", max_length=200, description="Name or category text; empty = anything nearby")
    near: GeoPoint
    radius_m: int = Field(default=5_000, ge=100, le=50_000)
    categories: list[PlaceCategory] = []
    limit: int = Field(default=20, ge=1, le=100)


@router.post("/search", response_model=list[Place])
def search_places(payload: PlaceSearch, places: Places) -> list[Place]:
    results = places.search(
        payload.query, payload.near, radius_m=payload.radius_m, categories=payload.categories or None
    )
    return results[: payload.limit]


@router.get("/{place_id}", response_model=Place)
def get_place(place_id: Annotated[str, Path(max_length=300, examples=["mock:karnak"])], places: Places) -> Place:
    place = places.details(place_id)
    if place is None:
        raise NotFound(f"place {place_id} not found")
    return place
