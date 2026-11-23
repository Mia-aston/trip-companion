"""Plan a trip in memory: day inputs → planner → materialise → validate (AI-002 adds persistence)."""

from dataclasses import dataclass, field
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.domain.itinerary.days import DayPlanInput, StopContext, plan_day_inputs
from app.domain.itinerary.plan import PlanDay, PlanItem, ProposedPlan, booking_items, materialize
from app.domain.itinerary.planner import FixedBlock, Planner, PlannerContext, PlannerDay
from app.domain.itinerary.validator import Violation, validate
from app.domain.places.models import Place
from app.domain.trips.models import Trip
from app.orchestration.day_candidates import fetch_stop_contexts
from app.providers.base import PlacesProvider, RoutesProvider


@dataclass
class PlanResult:
    plan: list[PlanDay]
    proposed: ProposedPlan
    violations: list[Violation]
    day_inputs: dict[date, DayPlanInput]
    places: dict[str, Place] = field(default_factory=dict)


def _block(item: PlanItem, day: date, tz: ZoneInfo) -> FixedBlock | None:
    start, end = item.starts_at.astimezone(tz).replace(tzinfo=None), item.ends_at.astimezone(tz).replace(tzinfo=None)
    day_start, day_end = datetime.combine(day, time(0)), datetime.combine(day, time(23, 59))
    start, end = max(start, day_start), min(end, day_end)
    if end <= start:
        return None
    return FixedBlock(start=start.time(), end=end.time(), title=item.title, place_id=item.place_id)


def plan_trip(
    trip: Trip,
    places: PlacesProvider,
    routes: RoutesProvider,
    planner: Planner,
    *,
    keep: dict[date, list[PlanItem]] | None = None,
    previous: list[PlanDay] | None = None,
    note: str = "",
) -> PlanResult:
    contexts: dict[int, StopContext] = fetch_stop_contexts(trip, places, routes)
    day_inputs = {d.date: d for d in plan_day_inputs(trip, contexts).days}
    keep = keep or {}

    planner_days = []
    for d in day_inputs.values():
        tz = ZoneInfo(d.timezone)
        fixed = [b for i in booking_items(trip, d.date, tz) + keep.get(d.date, []) if (b := _block(i, d.date, tz))]
        ctx = contexts.get(d.stop_seq)
        planner_days.append(
            PlannerDay(
                input=d,
                fixed=fixed,
                places=[p for p in (ctx.places if ctx else []) if p.id in {c.place_id for c in d.candidates}],
                matrix=ctx.matrix if ctx else None,
            )
        )
    proposed = planner.compose(PlannerContext(days=planner_days, note=note))
    plan = materialize(trip, proposed, [(d.date, d.stop_seq, d.timezone) for d in day_inputs.values()], keep)

    all_places = {p.id: p for ctx in contexts.values() for p in ctx.places}

    def travel(a: str, b: str) -> int | None:
        for ctx in contexts.values():
            if ctx.matrix is not None and (m := ctx.matrix.minutes(a, b)) is not None:
                return m
        return None

    violations = validate(trip, plan, day_inputs, all_places, travel, previous)
    return PlanResult(plan=plan, proposed=proposed, violations=violations, day_inputs=day_inputs, places=all_places)
