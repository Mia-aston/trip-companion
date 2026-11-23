"""AI-002 pure parts: diff by item_key, key reuse, kept items."""

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from app.domain.itinerary.plan import ItemKind, ItemSource, PlanDay, PlanItem
from app.domain.itinerary.versions import compute_diff, kept_items, reuse_keys

D1, D2 = date(2026, 11, 5), date(2026, 11, 6)


def _item(title, *, source=ItemSource.PLANNER, kind=ItemKind.PLACE, hour=10, locked=False, d=D1, key=None):
    start = datetime(d.year, d.month, d.day, hour, tzinfo=UTC)
    return PlanItem(
        item_key=key or uuid4(),
        kind=kind,
        title=title,
        place_id=f"mock:{title}" if kind is ItemKind.PLACE else None,
        starts_at=start,
        ends_at=start + timedelta(hours=1),
        locked=locked,
        source=source,
    )


def _day(d, *items):
    return PlanDay(date=d, stop_seq=0, timezone="UTC", items=list(items))


def test_diff_added_removed_changed_unchanged():
    a, b, c = _item("a"), _item("b", hour=12), _item("c", hour=14)
    old = [_day(D1, a, b, c)]
    moved = b.model_copy(
        update={"starts_at": b.starts_at + timedelta(hours=1), "ends_at": b.ends_at + timedelta(hours=1)}
    )
    new_item = _item("d", d=D2)
    diff = compute_diff(old, [_day(D1, a, moved), _day(D2, new_item)], 1, 2)
    assert [r.title for r in diff.added] == ["d"]
    assert [r.title for r in diff.removed] == ["c"]
    assert [(r.title, r.fields) for r in diff.changed] == [("b", ["starts_at", "ends_at"])]
    assert diff.unchanged == 1 and diff.changed_dates == [D1, D2]


def test_first_version_diff_is_all_added():
    diff = compute_diff(None, [_day(D1, _item("a"))], None, 1)
    assert len(diff.added) == 1 and diff.from_version is None


def test_reuse_keys_matches_same_visit():
    old = _item("karnak", hour=9)
    new = _item("karnak", hour=11)
    out = reuse_keys([_day(D1, new)], [_day(D1, old)])
    assert out[0].items[0].item_key == old.item_key
    assert compute_diff([_day(D1, old)], out, 1, 2).changed[0].fields == ["starts_at", "ends_at"]


def test_reuse_keys_never_steals_user_or_other_day_keys():
    user = _item("walk", source=ItemSource.USER, kind=ItemKind.CUSTOM)
    other_day = _item("karnak", d=D2)
    out = reuse_keys([_day(D1, user, _item("karnak"))], [_day(D1, user), _day(D2, other_day)])
    assert out[0].items[1].item_key != other_day.item_key


def test_kept_items_are_locked_or_user_not_bookings():
    locked = _item("karnak", locked=True)
    user = _item("aswan", source=ItemSource.USER, kind=ItemKind.CUSTOM)
    planner = _item("souq")
    booking = _item("flight", kind=ItemKind.BOOKING, source=ItemSource.BOOKING, locked=True)
    assert kept_items([_day(D1, locked, user, planner, booking)]) == {D1: [locked, user]}
