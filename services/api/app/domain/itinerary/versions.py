"""Plan versions and diffs (AI-002, A-19). Pure.

Versions are immutable full snapshots; the diff between two versions is computed by stable `item_key`.
"""

from datetime import date
from enum import StrEnum
from uuid import UUID

from pydantic import Field

from app.domain.itinerary.plan import ItemKind, ItemSource, PlanDay, PlanItem
from app.domain.itinerary.validator import Violation
from app.domain.shared.models import Contract, UtcDatetime


class CreatedBy(StrEnum):
    PLANNER = "planner"
    USER = "user"
    SYSTEM = "system"


class ItemRef(Contract):
    item_key: UUID
    date: date
    title: str
    kind: ItemKind


class ItemChange(ItemRef):
    fields: list[str] = Field(description="Changed fields, e.g. starts_at, place_id, locked")


class PlanDiff(Contract):
    from_version: int | None
    to_version: int
    added: list[ItemRef] = []
    removed: list[ItemRef] = []
    changed: list[ItemChange] = []
    unchanged: int = 0
    changed_dates: list[date] = []


class PlanVersion(Contract):
    trip_id: UUID
    version: int = Field(ge=1)
    parent_version: int | None = None
    created_by: CreatedBy
    planner: str | None = None
    reason: str = ""
    explanation: str = ""
    warnings: list[Violation] = []
    diff: PlanDiff | None = None
    created_at: UtcDatetime | None = None
    days: list[PlanDay]


_COMPARED = ("kind", "title", "place_id", "booking_id", "starts_at", "ends_at", "locked", "weather_sensitive")


def _index(days: list[PlanDay]) -> dict[UUID, tuple[date, PlanItem]]:
    return {i.item_key: (d.date, i) for d in days for i in d.items}


def compute_diff(old: list[PlanDay] | None, new: list[PlanDay], from_version: int | None, to_version: int) -> PlanDiff:
    before, after = _index(old or []), _index(new)
    diff = PlanDiff(from_version=from_version, to_version=to_version)
    touched: set[date] = set()
    for key, (d, item) in after.items():
        if key not in before:
            diff.added.append(ItemRef(item_key=key, date=d, title=item.title, kind=item.kind))
            touched.add(d)
            continue
        old_d, old_item = before[key]
        fields = [f for f in _COMPARED if getattr(old_item, f) != getattr(item, f)] + (["date"] if old_d != d else [])
        if fields:
            diff.changed.append(ItemChange(item_key=key, date=d, title=item.title, kind=item.kind, fields=fields))
            touched |= {d, old_d}
        else:
            diff.unchanged += 1
    for key, (d, item) in before.items():
        if key not in after:
            diff.removed.append(ItemRef(item_key=key, date=d, title=item.title, kind=item.kind))
            touched.add(d)
    diff.changed_dates = sorted(touched)
    for bucket in (diff.added, diff.removed, diff.changed):
        bucket.sort(key=lambda r: (r.date, r.title))
    return diff


def reuse_keys(new: list[PlanDay], previous: list[PlanDay] | None) -> list[PlanDay]:
    """Give new planner items the key of the matching previous planner item (same date, kind, place/title).

    Keeps diffs meaningful when the planner re-proposes the same visit (a time change shows as `changed`).
    """
    if not previous:
        return new
    pool: dict[tuple, list[UUID]] = {}
    taken = {i.item_key for d in new for i in d.items if i.source is not ItemSource.PLANNER}
    for d in previous:
        for i in d.items:
            if i.source is ItemSource.PLANNER and i.item_key not in taken:
                pool.setdefault((d.date, i.kind, i.place_id or i.title), []).append(i.item_key)
    out = []
    for d in new:
        items = []
        for i in d.items:
            keys = pool.get((d.date, i.kind, i.place_id or i.title)) if i.source is ItemSource.PLANNER else None
            items.append(i.model_copy(update={"item_key": keys.pop(0)}) if keys else i)
        out.append(d.model_copy(update={"items": items}))
    return out


def kept_items(previous: list[PlanDay] | None) -> dict[date, list[PlanItem]]:
    """Items a full re-generate must carry over: locked items and the user's own items (bookings are rebuilt)."""
    keep: dict[date, list[PlanItem]] = {}
    for d in previous or []:
        for i in d.items:
            if i.kind is not ItemKind.BOOKING and (i.locked or i.source is ItemSource.USER):
                keep.setdefault(d.date, []).append(i)
    return keep
