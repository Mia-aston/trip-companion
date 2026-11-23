"""PLACE-003: DB-backed caching of places, search snapshots and route legs."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update

from app.db.cache import CachedPlacesProvider, CachedRoutesProvider
from app.db.models import PlaceRow, ProviderSnapshotRow, RouteLegRow
from app.domain.routing.models import TravelMode, Waypoint
from app.domain.shared.models import GeoPoint
from app.providers.mock_places import MockPlacesProvider
from app.providers.mock_routes import MockRoutesProvider

LUXOR = GeoPoint(lat=25.6872, lon=32.6396)


class Counting:
    """Wraps a provider and counts calls per method."""

    def __init__(self, inner):
        self.inner, self.name, self.calls = inner, inner.name, {}

    def __getattr__(self, attr):
        target = getattr(self.inner, attr)

        def wrapper(*args, **kwargs):
            self.calls[attr] = self.calls.get(attr, 0) + 1
            return target(*args, **kwargs)

        return wrapper


def test_search_is_cached_and_identical(session):
    inner = Counting(MockPlacesProvider())
    cache = CachedPlacesProvider(session, inner)
    first = cache.search("temple", LUXOR, radius_m=10_000)
    second = cache.search("temple", LUXOR, radius_m=10_000)
    assert inner.calls["search"] == 1
    assert [p.model_dump(exclude={"provenance"}) for p in second] == [
        p.model_dump(exclude={"provenance"}) for p in first
    ]
    assert session.scalar(select(func.count()).select_from(ProviderSnapshotRow)) == 1


def test_different_request_misses(session):
    inner = Counting(MockPlacesProvider())
    cache = CachedPlacesProvider(session, inner)
    cache.search("temple", LUXOR, radius_m=10_000)
    cache.search("museum", LUXOR, radius_m=10_000)
    assert inner.calls["search"] == 2


def test_expired_snapshot_refetches(session):
    inner = Counting(MockPlacesProvider())
    cache = CachedPlacesProvider(session, inner)
    cache.search("temple", LUXOR)
    session.execute(
        update(ProviderSnapshotRow).values(
            expires_at=datetime.now(UTC) - timedelta(seconds=1), fetched_at=datetime.now(UTC) - timedelta(days=2)
        )
    )
    cache.search("temple", LUXOR)
    assert inner.calls["search"] == 2


def test_places_upserted_once(session):
    cache = CachedPlacesProvider(session, MockPlacesProvider())
    cache.search("", LUXOR)
    cache.search("temple", LUXOR)
    names = session.scalars(select(PlaceRow.name).where(PlaceRow.name == "Karnak Temple")).all()
    assert names == ["Karnak Temple"]


def test_details_from_cache_round_trips_contract(session):
    inner = Counting(MockPlacesProvider())
    cache = CachedPlacesProvider(session, inner)
    original = MockPlacesProvider().details("mock:luxor-museum")
    cache.search("museum", LUXOR)
    cached = cache.details("mock:luxor-museum")
    assert inner.calls.get("details") is None  # served from DB
    assert cached.model_dump(exclude={"provenance"}) == original.model_dump(exclude={"provenance"})
    assert cached.opening_hours == original.opening_hours  # split hours survive JSONB


def test_stale_detail_returned_when_provider_lost_it(session):
    class Forgetful(MockPlacesProvider):
        def details(self, place_id):
            return None

    CachedPlacesProvider(session, MockPlacesProvider()).search("temple", LUXOR)
    session.execute(update(PlaceRow).values(fetched_at=datetime.now(UTC) - timedelta(days=30)))
    stale = CachedPlacesProvider(session, Forgetful()).details("mock:karnak")
    assert stale is not None and stale.provenance.fetched_at < datetime.now(UTC) - timedelta(days=29)


def test_route_matrix_cached(session):
    inner = Counting(MockRoutesProvider())
    cache = CachedRoutesProvider(session, inner)
    points = [
        Waypoint(id="mock:luxor", location=LUXOR),
        Waypoint(id="mock:karnak", location=GeoPoint(lat=25.7188, lon=32.6573)),
    ]
    first = cache.matrix(points, TravelMode.DRIVE)
    second = cache.matrix(points, TravelMode.DRIVE)
    assert inner.calls["matrix"] == 1
    assert second.minutes("mock:luxor", "mock:karnak") == first.minutes("mock:luxor", "mock:karnak")
    assert session.scalar(select(func.count()).select_from(RouteLegRow)) == 2
    cache.matrix(points, TravelMode.WALK)  # other mode → miss
    assert inner.calls["matrix"] == 2
