"""Feasibility validator (ITIN-002). Pure. Errors block persisting a plan (A-21); warnings are stored.

Rules V1–V9: docs/ARCHITECTURE.md#validator-itin-002--pure-errors-block-persisting-warnings-are-shown
"""

from collections.abc import Callable
from datetime import date, datetime, timedelta
from datetime import date as Date
from enum import StrEnum
from uuid import UUID

from app.domain.itinerary.days import DayPlanInput, is_avoided
from app.domain.itinerary.plan import TIMED_BOOKINGS, ItemKind, PlanDay, PlanItem, booking_item_key
from app.domain.places.models import Place, is_open_for
from app.domain.shared.models import Contract
from app.domain.trips.models import BookingStatus, Hardness, MustDo, Trip

TravelMinutes = Callable[[str, str], int | None]


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class Violation(Contract):
    rule: str
    severity: Severity
    date: Date | None = None
    item_key: UUID | None = None
    message: str


def has_errors(violations: list[Violation]) -> bool:
    return any(v.severity is Severity.ERROR for v in violations)


def _minutes(a: datetime, b: datetime) -> int:
    return int((b - a).total_seconds() // 60)


def validate(
    trip: Trip,
    plan: list[PlanDay],
    day_inputs: dict[date, DayPlanInput],
    places: dict[str, Place],
    travel: TravelMinutes,
    previous: list[PlanDay] | None = None,
) -> list[Violation]:
    out: list[Violation] = []

    def add(rule: str, severity: Severity, message: str, day: date | None = None, item: PlanItem | None = None):
        out.append(
            Violation(rule=rule, severity=severity, date=day, item_key=item.item_key if item else None, message=message)
        )

    for day in plan:
        inp = day_inputs.get(day.date)
        items = sorted(day.items, key=lambda i: (i.starts_at, i.ends_at))

        # V1 window
        for item in items:
            if item.kind is ItemKind.BOOKING:
                continue
            start, end = day.local(item.starts_at), day.local(item.ends_at)
            if inp is None or inp.window is None:
                add("V1", Severity.ERROR, f"'{item.title}' scheduled on a day without sightseeing time", day.date, item)
                continue
            w_start = datetime.combine(day.date, inp.window.start)
            w_end = datetime.combine(day.date, inp.window.end)
            if start < w_start or end > w_end:
                add(
                    "V1",
                    Severity.ERROR,
                    f"'{item.title}' {start:%H:%M}-{end:%H:%M} is outside the window "
                    f"{inp.window.start:%H:%M}-{inp.window.end:%H:%M}",
                    day.date,
                    item,
                )

        # V2 overlap (two bookings may overlap each other; that is the traveller's data)
        for a, b in zip(items, items[1:], strict=False):
            if b.starts_at < a.ends_at and not (a.kind is ItemKind.BOOKING and b.kind is ItemKind.BOOKING):
                add("V2", Severity.ERROR, f"'{b.title}' overlaps '{a.title}'", day.date, b)

        # V3 travel between consecutive located items
        located = [i for i in items if i.place_id]
        for a, b in zip(located, located[1:], strict=False):
            need = travel(a.place_id, b.place_id)
            gap = _minutes(a.ends_at, b.starts_at)
            if need is not None and gap < need:
                add(
                    "V3", Severity.ERROR, f"{gap} min from '{a.title}' to '{b.title}', travel needs {need}", day.date, b
                )

        # V4 opening hours, V8 avoid
        for item in items:
            if item.kind is not ItemKind.PLACE:
                continue
            place = places.get(item.place_id or "")
            if place is None:
                add("V4", Severity.WARNING, f"'{item.title}': place details unavailable", day.date, item)
                continue
            if is_avoided(trip, place):
                add("V8", Severity.ERROR, f"'{place.name}' is on your avoid list", day.date, item)
            ok = is_open_for(place, day.local(item.starts_at), _minutes(item.starts_at, item.ends_at))
            if ok is None:
                add(
                    "V4",
                    Severity.WARNING,
                    f"'{place.name}': opening hours unknown — check before going",
                    day.date,
                    item,
                )
            elif not ok:
                add("V4", Severity.ERROR, f"'{place.name}' is not open for the whole visit", day.date, item)

        # V9 capacity
        if inp is not None:
            used = sum(_minutes(i.starts_at, i.ends_at) for i in items if i.kind is ItemKind.PLACE)
            if used > inp.capacity_minutes:
                add(
                    "V9",
                    Severity.WARNING,
                    f"{used} min of visits exceeds the day's capacity ({inp.capacity_minutes})",
                    day.date,
                )

    # V5 bookings mirrored exactly; no stale booking items
    by_key = {i.item_key: (d, i) for d in plan for i in d.items}
    live = {b.id for b in trip.bookings if b.kind in TIMED_BOOKINGS and b.status is not BookingStatus.CANCELLED}
    for b in trip.bookings:
        if b.id not in live:
            continue
        found = by_key.get(booking_item_key(trip, b.id))
        if found is None:
            add("V5", Severity.ERROR, f"booking '{b.title}' is missing from the plan")
            continue
        day, item = found
        if (item.starts_at, item.ends_at, item.locked, item.kind) != (b.starts_at, b.ends_at, True, ItemKind.BOOKING):
            add("V5", Severity.ERROR, f"booking '{b.title}' was changed", day.date, item)
    for day in plan:
        for item in day.items:
            if item.kind is ItemKind.BOOKING and item.booking_id not in live:
                add("V5", Severity.ERROR, f"'{item.title}' refers to a cancelled or unknown booking", day.date, item)

    # V6 locked items unchanged vs previous version
    if previous:
        for day in previous:
            for old in day.items:
                if not old.locked or old.kind is ItemKind.BOOKING:
                    continue
                found = by_key.get(old.item_key)
                if found is None or not found[1].same_content(old):
                    add("V6", Severity.ERROR, f"locked item '{old.title}' was changed or removed", day.date, old)

    # V7 hard must-dos scheduled somewhere (or covered by a booking)
    scheduled = [
        (i, places.get(i.place_id or ""))
        for d in plan
        for i in d.items
        if i.kind in (ItemKind.PLACE, ItemKind.BOOKING, ItemKind.CUSTOM)
    ]
    for c in trip.constraints:
        if not isinstance(c, MustDo) or c.hardness is not Hardness.HARD:
            continue
        if not any(_must_do_met(c, item, place) for item, place in scheduled):
            add("V7", Severity.WARNING, f"must-do '{c.query or c.place_id}' is not scheduled")
    return out


def _must_do_met(c: MustDo, item: PlanItem, place: Place | None) -> bool:
    if c.place_id:
        return item.place_id == c.place_id
    q = (c.query or "").casefold()
    names = [item.title.casefold()] + ([place.name.casefold()] if place else [])
    return bool(q) and any(q in n or n in q for n in names)


def shift(item: PlanItem, minutes: int) -> PlanItem:
    """Test/helper: move an item in time."""
    delta = timedelta(minutes=minutes)
    return item.model_copy(update={"starts_at": item.starts_at + delta, "ends_at": item.ends_at + delta})
