"""Planner interface + deterministic GreedyPlanner (AI-001, A-18). Pure.

A Planner turns a bounded `PlannerContext` into a `ProposedPlan`. The orchestrator materialises and validates
it; a plan with validator errors is never stored (A-21). An LLM planner (D-07) implements the same Protocol.
"""

from datetime import date, datetime, time, timedelta
from typing import Protocol

from pydantic import Field

from app.domain.itinerary.days import DayPlanInput
from app.domain.itinerary.plan import ItemKind, ProposedDay, ProposedItem, ProposedPlan
from app.domain.places.models import Place, is_open_for
from app.domain.routing.models import RouteMatrix
from app.domain.shared.models import Contract

MAX_CANDIDATES = 15
STEP = timedelta(minutes=15)
LUNCH = (time(12, 30), time(14, 30), 60)  # earliest start, latest end, minutes
DINNER = (time(19, 0), time(21, 0), 60)


class FixedBlock(Contract):
    """Time the planner must leave alone (bookings, locked/kept items, blocked intervals). Local times."""

    start: time
    end: time
    title: str
    place_id: str | None = None


class PlannerDay(Contract):
    input: DayPlanInput
    fixed: list[FixedBlock] = []
    exclude_place_ids: list[str] = []
    places: list[Place] = Field(default=[], description="Details for the day's candidates (hours)")
    matrix: RouteMatrix | None = None


class PlannerContext(Contract):
    days: list[PlannerDay]
    already_planned_place_ids: list[str] = Field(default=[], description="Visited on days outside the scope")
    note: str = ""


class Planner(Protocol):
    name: str

    def compose(self, context: PlannerContext) -> ProposedPlan: ...


def _overlaps(a: datetime, b: datetime, busy: list[tuple[datetime, datetime]]) -> bool:
    return any(a < y and x < b for x, y in busy)


class GreedyPlanner:
    """Must-dos first, then by score; earliest feasible slot after travel; meals; stop at capacity."""

    name = "greedy"

    def compose(self, context: PlannerContext) -> ProposedPlan:
        used_places: set[str] = set(context.already_planned_place_ids)  # a place is visited once per trip
        days = []
        for d in context.days:
            day = self._day(d, used_places)
            used_places |= {i.place_id for i in day.items if i.place_id}
            days.append(day)
        scheduled = sum(1 for d in days for i in d.items if i.kind is ItemKind.PLACE)
        explanation = (
            f"{scheduled} visits across {len(days)} day(s): must-dos first, then places that match your interests "
            "and ratings, kept inside opening hours and your day window, with travel time between stops."
        )
        return ProposedPlan(days=days, explanation=explanation)

    def _day(self, pd: PlannerDay, used_places: set[str]) -> ProposedDay:
        inp = pd.input
        if inp.window is None or inp.capacity_minutes == 0:
            return ProposedDay(date=inp.date, items=[])
        day: date = inp.date
        w_start, w_end = datetime.combine(day, inp.window.start), datetime.combine(day, inp.window.end)
        busy = [(datetime.combine(day, b.start), datetime.combine(day, b.end)) for b in inp.blocked]
        busy += [(datetime.combine(day, f.start), datetime.combine(day, f.end)) for f in pd.fixed]
        items: list[ProposedItem] = []

        for earliest, latest, minutes in (LUNCH, DINNER):
            slot = self._slot(
                datetime.combine(day, earliest), datetime.combine(day, latest), minutes, w_start, w_end, busy
            )
            if slot:
                busy.append(slot)
                title = "Lunch break" if earliest == LUNCH[0] else "Dinner"
                items.append(ProposedItem(kind=ItemKind.MEAL, title=title, start=slot[0].time(), end=slot[1].time()))

        # located fixed items (kept/locked visits): travel to and from them must fit too
        located = [
            (datetime.combine(day, f.start), datetime.combine(day, f.end), f.place_id) for f in pd.fixed if f.place_id
        ]
        places = {p.id: p for p in pd.places}
        excluded = set(pd.exclude_place_ids) | {f.place_id for f in pd.fixed if f.place_id} | used_places
        ranked = [c for c in inp.candidates if c.fits and c.place_id not in excluded]
        ranked.sort(key=lambda c: (not c.must_do, -c.score, c.name))
        cursor, here, used = w_start, inp.base_place_id, 0

        for cand in ranked[:MAX_CANDIDATES]:
            if used + cand.visit_minutes > inp.capacity_minutes:
                continue
            travel = self._travel(pd.matrix, here, cand.place_id, cand.travel_minutes)
            place = places.get(cand.place_id)
            start = cursor + timedelta(minutes=travel)
            start = start + (-(start - datetime.min) % STEP)  # round up to the next quarter hour
            visit = timedelta(minutes=cand.visit_minutes)
            while start + visit <= w_end:
                end = start + visit
                if (
                    not _overlaps(start, end, busy)
                    and (place is None or is_open_for(place, start, cand.visit_minutes) is not False)
                    and self._travel_fits(start, end, cand.place_id, located, pd.matrix)
                ):
                    break
                start += STEP
            else:
                continue
            busy.append((start, end))
            located.append((start, end, cand.place_id))
            items.append(
                ProposedItem(
                    kind=ItemKind.PLACE,
                    title=cand.name,
                    place_id=cand.place_id,
                    start=start.time(),
                    end=end.time(),
                    why="; ".join(cand.reasons[:3]),
                )
            )
            cursor, here, used = end, cand.place_id, used + cand.visit_minutes

        items.sort(key=lambda i: i.start)
        return ProposedDay(date=day, items=items)

    @staticmethod
    def _travel_fits(start, end, place_id, located, matrix) -> bool:
        """Enough drive time from the previous located item and to the next one (V3)."""
        before = [x for x in located if x[1] <= start]
        after = [x for x in located if x[0] >= end]
        if before:
            prev = max(before, key=lambda x: x[1])
            need = matrix.minutes(prev[2], place_id) if matrix else None
            if need is not None and start < prev[1] + timedelta(minutes=need):
                return False
        if after:
            nxt = min(after, key=lambda x: x[0])
            need = matrix.minutes(place_id, nxt[2]) if matrix else None
            if need is not None and nxt[0] < end + timedelta(minutes=need):
                return False
        return True

    @staticmethod
    def _travel(matrix: RouteMatrix | None, origin: str | None, dest: str, fallback: int) -> int:
        if matrix is not None and origin is not None:
            minutes = matrix.minutes(origin, dest)
            if minutes is not None:
                return minutes
        return fallback

    @staticmethod
    def _slot(earliest, latest, minutes, w_start, w_end, busy):
        start, length = max(earliest, w_start), timedelta(minutes=minutes)
        while start + length <= min(latest, w_end):
            if not _overlaps(start, start + length, busy):
                return start, start + length
            start += STEP
        return None
