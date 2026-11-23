"""User edits on a plan (ITIN-003). Pure: each returns new days; the orchestrator validates and stores a version.

Rules: bookings are never edited here; locked items must be unlocked before they are moved or deleted;
adding or moving a user item drops overlapping *unlocked planner* items on that day (the user's choice wins).
"""

from datetime import date, datetime, time
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from app.domain.itinerary.plan import ItemKind, ItemSource, PlanDay, PlanItem, booking_items
from app.domain.shared.errors import Conflict, InvalidChange, NotFound
from app.domain.trips.models import Trip


def find(days: list[PlanDay], item_key: UUID) -> tuple[PlanDay, PlanItem]:
    for d in days:
        for i in d.items:
            if i.item_key == item_key:
                return d, i
    raise NotFound(f"item {item_key} not found in the current plan")


def _editable(item: PlanItem) -> None:
    if item.kind is ItemKind.BOOKING:
        raise Conflict(f"'{item.title}' is a booking — change it under the trip's bookings")
    if item.locked:
        raise Conflict(f"'{item.title}' is locked — unlock it first")


def _replace_day(days: list[PlanDay], day: PlanDay) -> list[PlanDay]:
    return [day if d.date == day.date else d for d in days]


def _with_items(day: PlanDay, items: list[PlanItem]) -> PlanDay:
    return day.model_copy(update={"items": sorted(items, key=lambda i: (i.starts_at, i.ends_at, str(i.item_key)))})


def _drop_overlapping_planner_items(day: PlanDay, item: PlanItem) -> list[PlanItem]:
    return [
        i
        for i in day.items
        if i.item_key == item.item_key
        or not (
            i.source is ItemSource.PLANNER
            and not i.locked
            and i.starts_at < item.ends_at
            and item.starts_at < i.ends_at
        )
    ]


def _instant(day: PlanDay, t: time) -> datetime:
    return datetime.combine(day.date, t, ZoneInfo(day.timezone))


def add_item(
    days: list[PlanDay], on: date, title: str, start: time, end: time, place_id: str | None = None
) -> tuple[list[PlanDay], PlanItem]:
    day = next((d for d in days if d.date == on), None)
    if day is None:
        raise InvalidChange("Item rejected", [f"{on} is not a day of this trip"])
    if end <= start:
        raise InvalidChange("Item rejected", ["end must be after start"])
    item = PlanItem(
        item_key=uuid4(),
        kind=ItemKind.PLACE if place_id else ItemKind.CUSTOM,
        title=title,
        place_id=place_id,
        starts_at=_instant(day, start),
        ends_at=_instant(day, end),
        source=ItemSource.USER,
    )
    kept = _drop_overlapping_planner_items(day.model_copy(update={"items": [*day.items, item]}), item)
    return _replace_day(days, _with_items(day, kept)), item


def edit_item(
    days: list[PlanDay], item_key: UUID, *, title: str | None = None, start: time | None = None, end: time | None = None
) -> tuple[list[PlanDay], PlanItem]:
    day, item = find(days, item_key)
    _editable(item)
    local_start = day.local(item.starts_at).time() if start is None else start
    local_end = day.local(item.ends_at).time() if end is None else end
    if local_end <= local_start:
        raise InvalidChange("Item rejected", ["end must be after start"])
    changed = item.model_copy(
        update={
            "title": title or item.title,
            "starts_at": _instant(day, local_start),
            "ends_at": _instant(day, local_end),
            "source": ItemSource.USER,  # the user now owns this item; generate keeps it
        }
    )
    items = [changed if i.item_key == item_key else i for i in day.items]
    kept = _drop_overlapping_planner_items(day.model_copy(update={"items": items}), changed)
    return _replace_day(days, _with_items(day, kept)), changed


def delete_item(days: list[PlanDay], item_key: UUID) -> tuple[list[PlanDay], PlanItem]:
    day, item = find(days, item_key)
    _editable(item)
    return _replace_day(days, _with_items(day, [i for i in day.items if i.item_key != item_key])), item


def set_lock(days: list[PlanDay], item_key: UUID, locked: bool) -> tuple[list[PlanDay], PlanItem]:
    day, item = find(days, item_key)
    if item.kind is ItemKind.BOOKING:
        raise Conflict(f"'{item.title}' is a booking and always locked")
    changed = item.model_copy(update={"locked": locked})
    return _replace_day(days, _with_items(day, [changed if i.item_key == item_key else i for i in day.items])), changed


def refresh_bookings(trip: Trip, days: list[PlanDay]) -> list[PlanDay]:
    """Booking items always mirror the trip's current bookings (added, moved or cancelled since the last version)."""
    out = []
    for d in days:
        others = [i for i in d.items if i.kind is not ItemKind.BOOKING]
        out.append(_with_items(d, booking_items(trip, d.date, ZoneInfo(d.timezone)) + others))
    return out
