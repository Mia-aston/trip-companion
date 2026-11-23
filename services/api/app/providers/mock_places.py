"""Deterministic places provider over sanitized fixtures (tests/fixtures/places/*.json)."""

import json
from functools import cache
from pathlib import Path

from app.domain.places.models import Place, PlaceCategory
from app.domain.routing.geo import haversine_m
from app.domain.shared.models import GeoPoint

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "places"


@cache
def _load() -> tuple[Place, ...]:
    places: list[Place] = []
    for path in sorted(FIXTURES.glob("*.json")):
        places += [Place.model_validate(p) for p in json.loads(path.read_text())]
    return tuple(places)


class MockPlacesProvider:
    name = "mock"

    def search(
        self, query: str, near: GeoPoint, *, radius_m: int = 25_000, categories: list[PlaceCategory] | None = None
    ) -> list[Place]:
        """Places within radius whose name/category matches the query ('' = any), nearest first."""
        q = query.strip().casefold()
        hits = []
        for p in _load():
            if q and q not in p.name.casefold() and not any(q in c.value for c in p.categories):
                continue
            if categories and not set(categories) & set(p.categories):
                continue
            distance = haversine_m(near, p.location)
            if distance <= radius_m:
                hits.append((distance, p))
        return [p for _, p in sorted(hits, key=lambda h: (h[0], h[1].id))]

    def details(self, place_id: str) -> Place | None:
        return next((p for p in _load() if p.id == place_id), None)

    def resolve_city(self, city: str) -> Place | None:
        """The `city` place for a stop's city name (A-16)."""
        c = city.strip().casefold()
        return next(
            (p for p in _load() if PlaceCategory.CITY in p.categories and p.city and p.city.casefold() == c), None
        )
