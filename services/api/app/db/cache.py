"""Caching wrappers around provider adapters (PLACE-003). Same protocols as the providers they wrap.

- places: normalized `Place` rows + a `provider_snapshots` row per search (result ids, TTL);
- routes: `route_legs` per (provider, mode, origin, destination) with TTL.
Only normalized data is stored, never raw provider payloads (PROVIDERS.md).
"""

import hashlib
import json
from datetime import UTC, datetime, timedelta

from geoalchemy2 import Geometry
from sqlalchemy import cast, func, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import PlaceRow, ProviderSnapshotRow, RouteLegRow
from app.domain.places.models import Place, PlaceCategory
from app.domain.routing.models import RouteLeg, RouteMatrix, TravelMode, Waypoint
from app.domain.shared.models import GeoPoint, Provenance
from app.providers.base import PlacesProvider, RoutesProvider

SEARCH_TTL = timedelta(hours=24)
PLACE_TTL = timedelta(days=7)
ROUTE_TTL = timedelta(days=7)


def _now() -> datetime:
    return datetime.now(UTC)


def _hash(request: dict) -> str:
    return hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()


def _place_values(p: Place) -> dict:
    return dict(
        provider=p.provider,
        provider_place_id=p.provider_place_id,
        name=p.name,
        city=p.city,
        location=f"SRID=4326;POINT({p.location.lon} {p.location.lat})",
        categories=[c.value for c in p.categories],
        opening_hours=None if p.opening_hours is None else [o.model_dump(mode="json") for o in p.opening_hours],
        rating=p.rating,
        rating_count=p.rating_count,
        price_level=p.price_level,
        wheelchair_accessible=p.wheelchair_accessible,
        timezone=p.timezone,
        typical_visit_minutes=p.typical_visit_minutes,
        fetched_at=p.provenance.fetched_at or _now(),
    )


def _place(row: PlaceRow, lat: float, lon: float) -> Place:
    return Place(
        id=f"{row.provider}:{row.provider_place_id}",
        provider=row.provider,
        provider_place_id=row.provider_place_id,
        name=row.name,
        city=row.city,
        location=GeoPoint(lat=lat, lon=lon),
        categories=row.categories,
        opening_hours=row.opening_hours,
        rating=row.rating,
        rating_count=row.rating_count,
        price_level=row.price_level,
        wheelchair_accessible=row.wheelchair_accessible,
        timezone=row.timezone,
        typical_visit_minutes=row.typical_visit_minutes,
        provenance=Provenance(source="provider", provider=row.provider, fetched_at=row.fetched_at),
    )


class CachedPlacesProvider:
    def __init__(self, session: Session, inner: PlacesProvider) -> None:
        self.session, self.inner, self.name = session, inner, inner.name

    # --- protocol ---

    def search(
        self, query: str, near: GeoPoint, *, radius_m: int = 25_000, categories: list[PlaceCategory] | None = None
    ) -> list[Place]:
        request = {
            "query": query.strip().casefold(),
            "near": [round(near.lat, 3), round(near.lon, 3)],  # ~100 m buckets
            "radius_m": radius_m,
            "categories": sorted(c.value for c in categories or []),
        }
        key = _hash(request)
        snap = self.session.scalars(
            select(ProviderSnapshotRow).where(
                ProviderSnapshotRow.provider == self.name,
                ProviderSnapshotRow.kind == "places.search",
                ProviderSnapshotRow.request_hash == key,
            )
        ).one_or_none()
        if snap and snap.expires_at > _now():
            cached = self._load(snap.result_ids)
            if len(cached) == len(snap.result_ids):
                return cached
        places = self.inner.search(query, near, radius_m=radius_m, categories=categories)
        self._upsert(places)
        now = _now()
        values = dict(request=request, result_ids=[p.id for p in places], fetched_at=now, expires_at=now + SEARCH_TTL)
        stmt = insert(ProviderSnapshotRow).values(provider=self.name, kind="places.search", request_hash=key, **values)
        self.session.execute(
            stmt.on_conflict_do_update(index_elements=["provider", "kind", "request_hash"], set_=values)
        )
        return places

    def details(self, place_id: str) -> Place | None:
        cached = self._load([place_id])
        if cached and cached[0].provenance.fetched_at > _now() - PLACE_TTL:
            return cached[0]
        place = self.inner.details(place_id)
        if place is not None:
            self._upsert([place])
        return place or (cached[0] if cached else None)  # stale beats nothing if the provider lost it

    def resolve_city(self, city: str) -> Place | None:
        place = self.inner.resolve_city(city)
        if place is not None:
            self._upsert([place])
        return place

    # --- storage ---

    def _load(self, ids: list[str]) -> list[Place]:
        keys = [tuple(i.split(":", 1)) for i in ids if ":" in i]
        if not keys:
            return []
        point = cast(PlaceRow.location, Geometry)
        rows = self.session.execute(
            select(PlaceRow, func.ST_Y(point), func.ST_X(point)).where(
                tuple_(PlaceRow.provider, PlaceRow.provider_place_id).in_(keys)
            )
        ).all()
        by_id = {f"{r.provider}:{r.provider_place_id}": (r, lat, lon) for r, lat, lon in rows}
        return [_place(*by_id[i]) for i in ids if i in by_id]

    def _upsert(self, places: list[Place]) -> None:
        if not places:
            return
        for p in places:
            values = _place_values(p)
            stmt = insert(PlaceRow).values(**values)
            update = {k: v for k, v in values.items() if k not in ("provider", "provider_place_id")}
            self.session.execute(
                stmt.on_conflict_do_update(index_elements=["provider", "provider_place_id"], set_=update)
            )
        self.session.flush()


class CachedRoutesProvider:
    def __init__(self, session: Session, inner: RoutesProvider) -> None:
        self.session, self.inner, self.name = session, inner, inner.name

    def matrix(self, waypoints: list[Waypoint], mode: TravelMode) -> RouteMatrix:
        ids = [w.id for w in waypoints]
        wanted = {(a, b) for a in ids for b in ids if a != b}
        rows = self.session.scalars(
            select(RouteLegRow).where(
                RouteLegRow.provider == self.name,
                RouteLegRow.mode == mode.value,
                RouteLegRow.origin_id.in_(ids),
                RouteLegRow.destination_id.in_(ids),
                RouteLegRow.fetched_at > _now() - ROUTE_TTL,
            )
        ).all()
        fresh = {(r.origin_id, r.destination_id): r for r in rows}
        if wanted <= set(fresh):
            legs = [
                RouteLeg(origin_id=o, destination_id=d, duration_s=r.duration_s, distance_m=r.distance_m)
                for (o, d), r in sorted(fresh.items())
                if (o, d) in wanted
            ]
            oldest = min((fresh[p].fetched_at for p in wanted), default=_now())
            provenance = Provenance(source="provider", provider=self.name, fetched_at=oldest)
            return RouteMatrix(mode=mode, legs=legs, provenance=provenance)

        matrix = self.inner.matrix(waypoints, mode)
        fetched = matrix.provenance.fetched_at or _now()
        for leg in matrix.legs:
            values = dict(duration_s=leg.duration_s, distance_m=leg.distance_m, fetched_at=fetched)
            stmt = insert(RouteLegRow).values(
                provider=self.name,
                mode=mode.value,
                origin_id=leg.origin_id,
                destination_id=leg.destination_id,
                **values,
            )
            self.session.execute(
                stmt.on_conflict_do_update(
                    index_elements=["provider", "mode", "origin_id", "destination_id"], set_=values
                )
            )
        self.session.flush()
        return matrix
