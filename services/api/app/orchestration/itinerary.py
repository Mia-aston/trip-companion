"""Plan a trip in memory: day inputs → planner → materialise → validate (AI-002 adds persistence)."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import TYPE_CHECKING
from uuid import UUID
from zoneinfo import ZoneInfo

from app.domain.itinerary.days import DayPlanInput, StopContext, plan_day_inputs
from app.domain.itinerary.edits import refresh_bookings
from app.domain.itinerary.plan import ItemKind, ItemSource, PlanDay, PlanItem, ProposedPlan, booking_items, materialize
from app.domain.itinerary.planner import FixedBlock, Planner, PlannerContext, PlannerDay
from app.domain.itinerary.validator import Severity, Violation, has_errors, validate
from app.domain.itinerary.versions import CreatedBy, PlanVersion, compute_diff, kept_items, reuse_keys
from app.domain.places.models import Place
from app.domain.routing.geo import haversine_m
from app.domain.shared.errors import InvalidChange, NotFound
from app.domain.shared.models import Pace
from app.domain.trips.models import Trip
from app.orchestration.day_candidates import fetch_stop_contexts
from app.providers.base import PlacesProvider, RoutesProvider

if TYPE_CHECKING:
    from app.db.plans import PlanRepository


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


@dataclass
class Workspace:
    """Everything needed to plan or validate a trip: stop contexts, day inputs, places, travel times."""

    contexts: dict[int, StopContext]
    day_inputs: dict[date, DayPlanInput]
    places: dict[str, Place]

    def travel(self, a: str, b: str) -> int | None:
        for ctx in self.contexts.values():
            if ctx.matrix is not None and (m := ctx.matrix.minutes(a, b)) is not None:
                return m
        return None


def workspace(trip: Trip, places: PlacesProvider, routes: RoutesProvider) -> Workspace:
    contexts = fetch_stop_contexts(trip, places, routes)
    day_inputs = {d.date: d for d in plan_day_inputs(trip, contexts).days}
    return Workspace(contexts, day_inputs, {p.id: p for ctx in contexts.values() for p in ctx.places})


def plan_trip(
    trip: Trip,
    places: PlacesProvider,
    routes: RoutesProvider,
    planner: Planner,
    *,
    keep: dict[date, list[PlanItem]] | None = None,
    previous: list[PlanDay] | None = None,
    note: str = "",
    scope: set[date] | None = None,
    exclude_place_ids: list[str] | None = None,
    stay_within_m: int | None = None,
) -> PlanResult:
    """Plan the dates in `scope` (all dates when None); out-of-scope dates get only their `keep` items."""
    ws = workspace(trip, places, routes)
    keep = keep or {}
    in_scope = scope if scope is not None else set(ws.day_inputs)
    planned_elsewhere = [i.place_id for d, items in keep.items() if d not in in_scope for i in items if i.place_id]

    planner_days = []
    for d in ws.day_inputs.values():
        if d.date not in in_scope:
            continue
        tz = ZoneInfo(d.timezone)
        fixed = [b for i in booking_items(trip, d.date, tz) + keep.get(d.date, []) if (b := _block(i, d.date, tz))]
        ctx = ws.contexts.get(d.stop_seq)
        day_input = d
        if stay_within_m is not None and ctx is not None and ctx.base is not None:
            near = {p.id for p in ctx.places if haversine_m(ctx.base.location, p.location) <= stay_within_m}
            day_input = d.model_copy(update={"candidates": [c for c in d.candidates if c.place_id in near]})
        planner_days.append(
            PlannerDay(
                input=day_input,
                pace=trip.pace.value,
                fixed=fixed,
                exclude_place_ids=exclude_place_ids or [],
                places=[p for p in (ctx.places if ctx else []) if p.id in {c.place_id for c in day_input.candidates}],
                matrix=ctx.matrix if ctx else None,
            )
        )
    proposed = planner.compose(
        PlannerContext(days=planner_days, already_planned_place_ids=planned_elsewhere, note=note)
    )
    plan = materialize(trip, proposed, [(d.date, d.stop_seq, d.timezone) for d in ws.day_inputs.values()], keep)
    plan = reuse_keys(plan, previous)
    violations = validate(trip, plan, ws.day_inputs, ws.places, ws.travel, previous)
    return PlanResult(plan=plan, proposed=proposed, violations=violations, day_inputs=ws.day_inputs, places=ws.places)


def violations_payload(violations: list[Violation]) -> list[dict]:
    return [v.model_dump(mode="json") for v in violations]


def _store(
    plans: "PlanRepository",
    trip: Trip,
    latest: PlanVersion | None,
    days: list[PlanDay],
    violations: list[Violation],
    day_inputs: dict[date, DayPlanInput],
    *,
    created_by: CreatedBy,
    reason: str,
    planner: str | None = None,
    explanation: str = "",
) -> PlanVersion:
    if has_errors(violations):
        errors = [v for v in violations if v.severity is Severity.ERROR]
        raise InvalidChange("Plan failed validation", violations_payload(errors))
    version = plans.next_version(trip.id)
    plan = PlanVersion(
        trip_id=trip.id,
        version=version,
        parent_version=latest.version if latest else None,
        created_by=created_by,
        planner=planner,
        reason=reason,
        explanation=explanation or (latest.explanation if latest else ""),
        warnings=violations,
        diff=compute_diff(latest.days if latest else None, days, latest.version if latest else None, version),
        days=days,
    )
    capacities = {d: inp.capacity_minutes for d, inp in day_inputs.items()}
    notes = {d: inp.notes for d, inp in day_inputs.items()}
    return plans.add(plan, capacities, notes)


def generate_version(
    trip: Trip,
    places: PlacesProvider,
    routes: RoutesProvider,
    planner: Planner,
    plans: "PlanRepository",
    *,
    note: str = "",
) -> PlanVersion:
    """Full (re)plan → validated new version. Keeps locked and user items from the latest version (A-19, A-21)."""
    latest = plans.get(trip.id)
    previous = latest.days if latest else None
    result = plan_trip(trip, places, routes, planner, keep=kept_items(previous), previous=previous, note=note)
    return _store(
        plans,
        trip,
        latest,
        result.plan,
        result.violations,
        result.day_inputs,
        created_by=CreatedBy.PLANNER,
        planner=planner.name,
        explanation=result.proposed.explanation,
        reason=note or ("Initial plan" if latest is None else "Re-generated plan"),
    )


def regenerate_day(
    trip: Trip,
    places: PlacesProvider,
    routes: RoutesProvider,
    planner: Planner,
    plans: "PlanRepository",
    *,
    on: date,
    remove_item_keys: list[UUID] | None = None,
    exclude_place_ids: list[str] | None = None,
    stay_within_m: int | None = None,
    pace: Pace | None = None,
    note: str = "",
) -> PlanVersion:
    """Re-plan one day (A-20). Bookings, locked items, user items not removed, and every other day are preserved."""
    latest = plans.get(trip.id)
    if latest is None:
        raise NotFound("no itinerary yet — generate one first")
    if not trip.start_date <= on <= trip.end_date:
        raise InvalidChange("Regenerate rejected", [f"{on} is not a day of this trip"])
    removed = set(remove_item_keys or [])
    current = refresh_bookings(trip, latest.days)
    known = {i.item_key for d in current for i in d.items}
    if unknown := removed - known:
        raise NotFound(f"items not in the current plan: {', '.join(sorted(map(str, unknown)))}")
    keep: dict[date, list[PlanItem]] = {}
    for d in current:
        for i in d.items:
            if i.kind is ItemKind.BOOKING:
                continue
            if d.date != on:
                keep.setdefault(d.date, []).append(i)  # out of scope: untouched
            elif i.locked or (i.source is ItemSource.USER and i.item_key not in removed):
                keep.setdefault(d.date, []).append(i)
    planning_trip = trip.model_copy(update={"pace": pace}) if pace else trip
    result = plan_trip(
        planning_trip,
        places,
        routes,
        planner,
        keep=keep,
        previous=current,
        note=note,
        scope={on},
        exclude_place_ids=exclude_place_ids,
        stay_within_m=stay_within_m,
    )
    return _store(
        plans,
        trip,
        latest,
        result.plan,
        result.violations,
        result.day_inputs,
        created_by=CreatedBy.PLANNER,
        planner=planner.name,
        explanation=result.proposed.explanation,
        reason=note or f"Re-planned {on:%d %b}",
    )


def apply_user_edit(
    trip: Trip,
    places: PlacesProvider,
    routes: RoutesProvider,
    plans: "PlanRepository",
    edit: Callable[[list[PlanDay]], tuple[list[PlanDay], PlanItem]],
    reason: Callable[[PlanItem], str],
) -> PlanVersion:
    """Apply a pure edit to the latest version, re-mirror bookings, validate (V6 not applied: the user decides)."""
    latest = plans.get(trip.id)
    if latest is None:
        raise NotFound("no itinerary yet — generate one first")
    days, item = edit(refresh_bookings(trip, latest.days))
    ws = workspace(trip, places, routes)
    violations = validate(trip, days, ws.day_inputs, ws.places, ws.travel)
    return _store(plans, trip, latest, days, violations, ws.day_inputs, created_by=CreatedBy.USER, reason=reason(item))
