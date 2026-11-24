"""Candidate day builder (ITIN-001). Pure: no I/O. Rules: docs/ARCHITECTURE.md#day-capacity-m2 (A-15).

Input: a Trip plus, per stop, the stop base, its nearby places and a route matrix (fetched by orchestration).
Output: per date, the available window, blocked intervals, capacity and ranked feasible candidates.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from pydantic import Field

from app.domain.places.models import Place, PlaceCategory, open_intervals
from app.domain.routing.models import RouteMatrix
from app.domain.shared.models import Contract, Interest, MobilityNeeds, Pace, TimeWindow
from app.domain.trips.models import Booking, BookingKind, BookingStatus, MustDo, Stop, TimeWindowConstraint, Trip

# --- tunable constants (A-15) ---------------------------------------------
ARRIVAL_BUFFER = timedelta(minutes=90)
DEPARTURE_BUFFER = timedelta(minutes=180)
UTILISATION = {Pace.RELAXED: 0.6, Pace.BALANCED: 0.75, Pace.PACKED: 0.9}
MOBILITY_FACTOR = 0.8
YOUNG_CHILD_FACTOR = 0.85
YOUNG_CHILD_AGE = 6
MIN_FREE_MINUTES = 60
WEIGHTS = {"interest": 0.5, "rating": 0.2, "must_do": 0.2, "travel": 0.1}
NEUTRAL_INTEREST = 0.3  # no interests declared
INTEREST_CATEGORIES: dict[Interest, set[PlaceCategory]] = {
    Interest.HISTORY: {
        PlaceCategory.MUSEUM,
        PlaceCategory.TEMPLE,
        PlaceCategory.ARCHAEOLOGICAL_SITE,
        PlaceCategory.LANDMARK,
    },
    Interest.FOOD: {PlaceCategory.RESTAURANT, PlaceCategory.CAFE, PlaceCategory.MARKET},
    Interest.PHOTO: {PlaceCategory.VIEWPOINT, PlaceCategory.LANDMARK, PlaceCategory.NATURE},
    Interest.NATURE: {PlaceCategory.NATURE, PlaceCategory.PARK},
    Interest.NIGHTLIFE: {PlaceCategory.NIGHTLIFE},
    Interest.SHOPPING: {PlaceCategory.MARKET, PlaceCategory.SHOPPING},
    Interest.ART: {PlaceCategory.ART, PlaceCategory.MUSEUM},
    Interest.ADVENTURE: {PlaceCategory.ACTIVITY, PlaceCategory.NATURE},
}


# --- contracts -------------------------------------------------------------


class BlockedInterval(Contract):
    start: time
    end: time
    label: str


class DayCandidate(Contract):
    place_id: str
    name: str
    categories: list[PlaceCategory]
    score: float = Field(ge=0, le=1)
    visit_minutes: int
    travel_minutes: int = Field(description="One way from the stop base")
    fits: bool = Field(description="travel there + visit + travel back <= capacity")
    must_do: bool
    hours_known: bool
    reasons: list[str]


class DayPlanInput(Contract):
    date: date
    stop_seq: int
    city: str
    timezone: str
    base_place_id: str | None = Field(default=None, description="Stop base (travel times start here)")
    window: TimeWindow | None = Field(description="None = no sightseeing time this day")
    blocked: list[BlockedInterval]
    free_minutes: int
    capacity_minutes: int
    candidates: list[DayCandidate]
    notes: list[str]


class TripDayCandidates(Contract):
    trip_id: str
    days: list[DayPlanInput]
    unmet_must_dos: list[str] = Field(description="Must-dos that fit on no day")


@dataclass(frozen=True)
class StopContext:
    """What orchestration fetched for one stop."""

    base: Place | None
    places: list[Place]
    matrix: RouteMatrix | None


# --- helpers ---------------------------------------------------------------


def _local(dt: datetime, tz: ZoneInfo) -> datetime:
    return dt.astimezone(tz).replace(tzinfo=None)


def _stop_for(trip: Trip, day: date) -> Stop:
    for stop in trip.stops:
        if stop.arrive_on <= day < stop.leave_on:
            return stop
    return trip.stops[-1]


def arrival_departure(trip: Trip) -> tuple[Booking | None, Booking | None]:
    """The trip's arrival flight (first) and departure flight (last), ignoring cancelled bookings."""
    flights = sorted(
        (b for b in trip.bookings if b.kind is BookingKind.FLIGHT and b.status is not BookingStatus.CANCELLED),
        key=lambda b: b.starts_at,
    )
    arrival = flights[0] if flights and flights[0].starts_at.date() < trip.end_date else None
    departure = flights[-1] if flights and flights[-1] is not arrival else None
    return arrival, departure


def _merge(intervals: Iterable[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    merged: list[tuple[datetime, datetime]] = []
    for a, b in sorted(intervals):
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def _minutes(a: datetime, b: datetime) -> int:
    return max(0, int((b - a).total_seconds() // 60))


def _matches_must_do(c: MustDo, place: Place) -> bool:
    if c.place_id:
        return c.place_id == place.id
    return bool(c.query) and c.query.casefold() in place.name.casefold()


def is_avoided(trip: Trip, place: Place) -> bool:
    for c in trip.constraints:
        if c.kind != "avoid":
            continue
        if c.query and c.query.casefold() in place.name.casefold():
            return True
        if c.category and any(c.category.casefold() == cat.value for cat in place.categories):
            return True
    return False


def _interest_score(trip: Trip, place: Place) -> float:
    if not trip.interests:
        return NEUTRAL_INTEREST
    wanted = set().union(*(INTEREST_CATEGORIES[i] for i in trip.interests))
    return 1.0 if wanted & set(place.categories) else 0.0


def _capacity(trip: Trip, free: int) -> int:
    if free < MIN_FREE_MINUTES:
        return 0
    factor = UTILISATION[trip.pace]
    if trip.mobility_needs is not MobilityNeeds.NONE:
        factor *= MOBILITY_FACTOR
    if trip.infants or any(age < YOUNG_CHILD_AGE for age in trip.children_ages):
        factor *= YOUNG_CHILD_FACTOR
    return int(free * factor)


# --- main ------------------------------------------------------------------


def plan_day_inputs(trip: Trip, stops: dict[int, StopContext]) -> TripDayCandidates:
    arrival, departure = arrival_departure(trip)
    days: list[DayPlanInput] = []
    must_do_fit: dict[str, bool] = {}
    must_dos = [c for c in trip.constraints if c.kind == "must_do"]
    for c in must_dos:
        must_do_fit.setdefault(c.query or c.place_id or "", _covered_by_booking(trip, c))

    day = trip.start_date
    while day <= trip.end_date:
        stop = _stop_for(trip, day)
        ctx = stops.get(stop.seq, StopContext(base=None, places=[], matrix=None))
        tz_name = stop.timezone or (ctx.base.timezone if ctx.base else "UTC")
        tz = ZoneInfo(tz_name)
        notes: list[str] = []

        start = datetime.combine(day, trip.day_window.start)
        end = datetime.combine(day, trip.day_window.end)
        if arrival:
            landed = _local(arrival.ends_at, tz)
            if day < landed.date():
                start = end  # not there yet
                notes.append("before arrival")
            elif day == landed.date():
                start = max(start, landed + ARRIVAL_BUFFER)
                notes.append(f"arrival {landed:%H:%M} + {ARRIVAL_BUFFER.seconds // 60} min")
        if departure:
            leaves = _local(departure.starts_at, tz)
            if day > leaves.date():
                end = start  # already left
            elif day == leaves.date():
                end = min(end, leaves - DEPARTURE_BUFFER)
                notes.append(f"departure {leaves:%H:%M} − {DEPARTURE_BUFFER.seconds // 60} min")

        if stop.seq > 0 and day == stop.arrive_on:
            transfers = [
                _local(b.ends_at, tz)
                for b in trip.bookings
                if b.kind is BookingKind.TRANSPORT
                and b.status is not BookingStatus.CANCELLED
                and _local(b.ends_at, tz).date() == day
            ]
            if transfers:
                start = max(start, max(transfers))  # time before the transfer belongs to the previous stop
                notes.append(f"transfer day: arrives {max(transfers):%H:%M}")
            else:
                notes.append("transfer day: add the transport booking so travel time is blocked")

        blocked: list[tuple[datetime, datetime, str]] = []
        if end > start:
            busy = [
                (b.starts_at, b.ends_at, b.title)
                for b in trip.bookings
                if b.kind in (BookingKind.ACTIVITY, BookingKind.TRANSPORT) and b.status is not BookingStatus.CANCELLED
            ] + [(c.starts_at, c.ends_at, c.label) for c in trip.constraints if isinstance(c, TimeWindowConstraint)]
            for a, b, label in busy:
                a, b = max(_local(a, tz), start), min(_local(b, tz), end)
                if b > a:
                    blocked.append((a, b, label))
        window_minutes = _minutes(start, end)
        busy_minutes = sum(_minutes(a, b) for a, b in _merge((a, b) for a, b, _ in blocked))
        free = max(0, window_minutes - busy_minutes)
        capacity = _capacity(trip, free)
        if capacity == 0:
            notes.append("no sightseeing capacity")

        candidates: list[DayCandidate] = []
        if capacity and ctx.base is not None:
            candidates = _rank(trip, day, start, end, capacity, ctx, must_dos)
            for c in must_dos:
                key = c.query or c.place_id or ""
                if any(x.must_do and x.fits and _matches_key(c, x) for x in candidates):
                    must_do_fit[key] = True
        elif ctx.base is None:
            notes.append(f"stop base for '{stop.city}' not found")

        days.append(
            DayPlanInput(
                date=day,
                stop_seq=stop.seq,
                city=stop.city,
                timezone=tz_name,
                base_place_id=ctx.base.id if ctx.base else None,
                window=TimeWindow(start=start.time(), end=end.time()) if capacity else None,
                blocked=[BlockedInterval(start=a.time(), end=b.time(), label=label) for a, b, label in blocked],
                free_minutes=free,
                capacity_minutes=capacity,
                candidates=candidates,
                notes=notes,
            )
        )
        day += timedelta(days=1)

    return TripDayCandidates(
        trip_id=str(trip.id), days=days, unmet_must_dos=[k for k, ok in must_do_fit.items() if not ok]
    )


def _covered_by_booking(trip: Trip, c: MustDo) -> bool:
    """A booked activity whose title matches the must-do satisfies it (e.g. 'Hot air balloon')."""
    if not c.query:
        return False
    q = c.query.casefold()
    return any(
        b.kind is BookingKind.ACTIVITY
        and b.status is not BookingStatus.CANCELLED
        and (b.title.casefold() in q or q in b.title.casefold())
        for b in trip.bookings
    )


def _matches_key(c: MustDo, candidate: DayCandidate) -> bool:
    if c.place_id:
        return c.place_id == candidate.place_id
    return bool(c.query) and c.query.casefold() in candidate.name.casefold()


def _rank(
    trip: Trip, day: date, start: datetime, end: datetime, capacity: int, ctx: StopContext, must_dos: list[MustDo]
) -> list[DayCandidate]:
    out = []
    for place in ctx.places:
        if PlaceCategory.CITY in place.categories or is_avoided(trip, place):
            continue
        if trip.mobility_needs is MobilityNeeds.WHEELCHAIR and place.wheelchair_accessible is False:
            continue
        visit = place.typical_visit_minutes
        intervals = open_intervals(place, start)
        if intervals is not None and not any(_minutes(max(a, start), min(b, end)) >= visit for a, b in intervals):
            continue  # closed (or not long enough) inside today's window
        travel = ctx.matrix.minutes(ctx.base.id, place.id) if ctx.matrix else None
        if travel is None:
            continue
        is_must = any(_matches_must_do(c, place) and (c.on_date in (None, day)) for c in must_dos)
        interest = _interest_score(trip, place)
        rating = place.rating / 5 if place.rating is not None else 0.5
        penalty = min(travel / 60, 1.0)
        score = (
            WEIGHTS["interest"] * interest
            + WEIGHTS["rating"] * rating
            + WEIGHTS["must_do"] * (1.0 if is_must else 0.0)
            - WEIGHTS["travel"] * penalty
        )
        reasons = []
        if interest == 1.0:
            reasons.append("matches your interests")
        if is_must:
            reasons.append("must-do")
        if place.rating is not None and place.rating >= 4.5:
            reasons.append(f"highly rated ({place.rating})")
        if intervals is None:
            reasons.append("opening hours unknown — check before going")
        reasons.append(f"{travel} min from {ctx.base.name}")
        out.append(
            DayCandidate(
                place_id=place.id,
                name=place.name,
                categories=place.categories,
                score=round(min(1.0, max(0.0, score)), 3),
                visit_minutes=visit,
                travel_minutes=travel,
                fits=2 * travel + visit <= capacity,
                must_do=is_must,
                hours_known=intervals is not None,
                reasons=reasons,
            )
        )
    return sorted(out, key=lambda c: (-c.score, c.name))
