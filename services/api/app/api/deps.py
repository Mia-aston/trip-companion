"""Shared FastAPI dependencies: providers are always wrapped in the DB cache (PLACE-003)."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.cache import CachedPlacesProvider, CachedRoutesProvider
from app.db.plans import PlanRepository
from app.db.session import get_session
from app.domain.itinerary.planner import GreedyPlanner, Planner
from app.providers import registry
from app.providers.base import PlacesProvider, RoutesProvider


def get_places(session: Annotated[Session, Depends(get_session)]) -> PlacesProvider:
    return CachedPlacesProvider(session, registry.places_provider())


def get_routes(session: Annotated[Session, Depends(get_session)]) -> RoutesProvider:
    return CachedRoutesProvider(session, registry.routes_provider())


Places = Annotated[PlacesProvider, Depends(get_places)]
Routes = Annotated[RoutesProvider, Depends(get_routes)]


def get_plans(session: Annotated[Session, Depends(get_session)]) -> PlanRepository:
    return PlanRepository(session)


def get_planner() -> Planner:
    """A-18: deterministic planner; an LLM planner (D-07) will be selectable here."""
    return GreedyPlanner()


Plans = Annotated[PlanRepository, Depends(get_plans)]
PlannerDep = Annotated[Planner, Depends(get_planner)]
