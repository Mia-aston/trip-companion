"""Deterministic route matrix: haversine × detour factor ÷ mode speed (+ pickup overhead for driving)."""

from datetime import UTC, datetime

from app.domain.routing.geo import haversine_m
from app.domain.routing.models import RouteLeg, RouteMatrix, TravelMode, Waypoint
from app.domain.shared.models import Provenance

DETOUR = 1.3  # straight line → street distance
SPEED_KMH = {TravelMode.WALK: 4.5, TravelMode.DRIVE: 30.0}  # city average incl. traffic
OVERHEAD_S = {TravelMode.WALK: 0, TravelMode.DRIVE: 5 * 60}  # finding / waiting for a taxi


class MockRoutesProvider:
    name = "mock"

    def matrix(self, waypoints: list[Waypoint], mode: TravelMode) -> RouteMatrix:
        legs = []
        for a in waypoints:
            for b in waypoints:
                if a.id == b.id:
                    continue
                distance = haversine_m(a.location, b.location) * DETOUR
                duration = distance / (SPEED_KMH[mode] * 1000 / 3600) + OVERHEAD_S[mode]
                legs.append(
                    RouteLeg(
                        origin_id=a.id, destination_id=b.id, duration_s=round(duration), distance_m=round(distance)
                    )
                )
        provenance = Provenance(source="provider", provider=self.name, fetched_at=datetime.now(UTC))
        return RouteMatrix(mode=mode, legs=legs, provenance=provenance)
