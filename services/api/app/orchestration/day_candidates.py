"""Fetch what the day builder needs from providers, then call the pure domain function (ITIN-001)."""

from app.domain.itinerary.days import StopContext, TripDayCandidates, plan_day_inputs
from app.domain.places.models import PlaceCategory
from app.domain.routing.models import TravelMode, Waypoint
from app.domain.trips.models import Trip
from app.providers.base import PlacesProvider, RoutesProvider

STOP_RADIUS_M = 25_000


def fetch_stop_contexts(trip: Trip, places: PlacesProvider, routes: RoutesProvider) -> dict[int, StopContext]:
    contexts: dict[int, StopContext] = {}
    for stop in trip.stops:
        base = places.resolve_city(stop.city)
        if base is None:
            contexts[stop.seq] = StopContext(base=None, places=[], matrix=None)
            continue
        nearby = [
            p
            for p in places.search("", base.location, radius_m=STOP_RADIUS_M)
            if PlaceCategory.CITY not in p.categories
        ]
        waypoints = [Waypoint(id=p.id, location=p.location) for p in [base, *nearby]]
        contexts[stop.seq] = StopContext(base=base, places=nearby, matrix=routes.matrix(waypoints, TravelMode.DRIVE))
    return contexts


def build_day_candidates(trip: Trip, places: PlacesProvider, routes: RoutesProvider) -> TripDayCandidates:
    return plan_day_inputs(trip, fetch_stop_contexts(trip, places, routes))
