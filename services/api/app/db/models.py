"""Persistence schema (SQLAlchemy ORM).

ORM rows stay inside the persistence layer. Other modules exchange typed domain
objects (see `app/db/repositories.py`), never these classes.
"""

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from geoalchemy2 import Geography
from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

Money = Numeric(14, 2)

# References to trip_members use the default NO ACTION (checked at end of statement), not RESTRICT:
# deleting a member who paid/owes is refused, but deleting a whole trip cascades through members,
# expenses and transfers in one statement.


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


CURRENCY_CHECK = "~ '^[A-Z]{3}$'"


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class UserRow(TimestampMixin, Base):
    """Minimal account (D-01: auth vendor TBD; M1 runs a single dev user)."""

    __tablename__ = "users"
    __table_args__ = (CheckConstraint(f"default_currency {CURRENCY_CHECK}", name="currency_iso"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    display_name: Mapped[str] = mapped_column(String(80))
    default_currency: Mapped[str] = mapped_column(String(3), default="GBP")
    locale: Mapped[str] = mapped_column(String(10), default="en")


class TripRow(TimestampMixin, Base):
    """Trip Core. Mirrors `app.domain.trips.models.Trip` (CORE-001); mapping in `repositories.py`."""

    __tablename__ = "trips"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="dates_ordered"),
        CheckConstraint("adults BETWEEN 1 AND 20", name="adults_range"),
        CheckConstraint("infants BETWEEN 0 AND adults", name="infants_per_adult"),
        CheckConstraint("adults + cardinality(children_ages) + infants <= 20", name="party_size"),
        CheckConstraint("day_end > day_start", name="day_window_ordered"),
        CheckConstraint("price_level BETWEEN 1 AND 4", name="price_level_range"),
        CheckConstraint(_in("status", ("draft", "planned", "active", "done")), name="status_valid"),
        CheckConstraint(_in("pace", ("relaxed", "balanced", "packed")), name="pace_valid"),
        CheckConstraint(
            _in("mobility_needs", ("none", "limited_walking", "wheelchair", "stroller")), name="mobility_valid"
        ),
        CheckConstraint(f"base_currency {CURRENCY_CHECK}", name="base_currency_iso"),
        CheckConstraint(f"settlement_currency {CURRENCY_CHECK}", name="settlement_currency_iso"),
        CheckConstraint(
            "(budget_amount IS NULL) = (budget_currency IS NULL) AND (budget_amount IS NULL) = (budget_scope IS NULL)",
            name="budget_complete",
        ),
        CheckConstraint(
            "budget_scope IS NULL OR " + _in("budget_scope", ("per_trip", "per_person")), name="budget_scope_valid"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(16), default="draft")
    origin: Mapped[str] = mapped_column(String(120))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    adults: Mapped[int] = mapped_column(default=1)
    children_ages: Mapped[list[int]] = mapped_column(ARRAY(SmallInteger), default=list, server_default="{}")
    infants: Mapped[int] = mapped_column(default=0)
    base_currency: Mapped[str] = mapped_column(String(3))
    settlement_currency: Mapped[str] = mapped_column(String(3))
    budget_amount: Mapped[Decimal | None] = mapped_column(Money)
    budget_currency: Mapped[str | None] = mapped_column(String(3))
    budget_scope: Mapped[str | None] = mapped_column(String(16))
    pace: Mapped[str] = mapped_column(String(16), default="balanced")
    day_start: Mapped[time] = mapped_column(Time)
    day_end: Mapped[time] = mapped_column(Time)
    interests: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")
    dietary: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")
    mobility_needs: Mapped[str] = mapped_column(String(20), default="none")
    price_level: Mapped[int] = mapped_column(SmallInteger, default=2)
    flight_prefs: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    stops: Mapped[list["TripStopRow"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="TripStopRow.seq"
    )
    members: Mapped[list["TripMemberRow"]] = relationship(
        back_populates="trip", cascade="all, delete-orphan", passive_deletes=True, order_by="TripMemberRow.position"
    )
    constraints: Mapped[list["TripConstraintRow"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="TripConstraintRow.position"
    )
    bookings: Mapped[list["BookingRow"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="(BookingRow.starts_at, BookingRow.id)"
    )


class TripStopRow(Base):
    """One destination in a multi-city trip. Dates are stored so itinerary queries need no recomputation."""

    __tablename__ = "trip_stops"
    __table_args__ = (
        UniqueConstraint("trip_id", "seq"),
        CheckConstraint("seq >= 0", name="seq_non_negative"),
        CheckConstraint("nights BETWEEN 0 AND 60", name="nights_range"),
        CheckConstraint("leave_on = arrive_on + nights", name="dates_match_nights"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    seq: Mapped[int] = mapped_column(SmallInteger)
    city: Mapped[str] = mapped_column(String(120))
    nights: Mapped[int] = mapped_column(SmallInteger)
    timezone: Mapped[str | None] = mapped_column(String(64))
    accommodation_area: Mapped[str | None] = mapped_column(String(200))
    arrive_on: Mapped[date] = mapped_column(Date)
    leave_on: Mapped[date] = mapped_column(Date)


class TripMemberRow(TimestampMixin, Base):
    """Someone who pays or owes on this trip (A-07). Not necessarily a traveller or a user."""

    __tablename__ = "trip_members"
    __table_args__ = (
        Index("uq_trip_members_trip_id_lower_display_name", "trip_id", func.lower(text("display_name")), unique=True),
        CheckConstraint(_in("role", ("owner", "editor", "viewer")), name="role_valid"),
        CheckConstraint(f"currency_pref IS NULL OR currency_pref {CURRENCY_CHECK}", name="currency_pref_iso"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    position: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    display_name: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(16), default="owner")
    currency_pref: Mapped[str | None] = mapped_column(String(3))

    trip: Mapped[TripRow] = relationship(back_populates="members")


class TripConstraintRow(TimestampMixin, Base):
    """must_do / avoid / time_window (A-09). Kind-specific fields live in `payload`, validated by the contract."""

    __tablename__ = "trip_constraints"
    __table_args__ = (
        CheckConstraint(_in("kind", ("must_do", "avoid", "time_window")), name="kind_valid"),
        CheckConstraint(_in("hardness", ("hard", "soft")), name="hardness_valid"),
        CheckConstraint(_in("source", ("user", "booking", "system")), name="source_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    kind: Mapped[str] = mapped_column(String(16))
    hardness: Mapped[str] = mapped_column(String(8), default="hard")
    source: Mapped[str] = mapped_column(String(16), default="user")
    locked: Mapped[bool] = mapped_column(default=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")


class BookingRow(TimestampMixin, Base):
    """Confirmed/tentative external booking, entered manually in MVP."""

    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("ends_at >= starts_at", name="times_ordered"),
        CheckConstraint("(cost_amount IS NULL) = (cost_currency IS NULL)", name="cost_complete"),
        CheckConstraint(f"cost_currency IS NULL OR cost_currency {CURRENCY_CHECK}", name="cost_currency_iso"),
        CheckConstraint(_in("kind", ("flight", "hotel", "activity", "transport")), name="kind_valid"),
        CheckConstraint(_in("status", ("confirmed", "tentative", "cancelled")), name="status_valid"),
        CheckConstraint("stop_seq IS NULL OR stop_seq >= 0", name="stop_seq_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(120))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    stop_seq: Mapped[int | None] = mapped_column(SmallInteger)
    location_name: Mapped[str | None] = mapped_column(String(200))
    reference: Mapped[str | None] = mapped_column(String(120))
    cost_amount: Mapped[Decimal | None] = mapped_column(Money)
    cost_currency: Mapped[str | None] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(16), default="confirmed")


class PlaceRow(TimestampMixin, Base):
    """Normalized place cache (PLACE-003). Domain id = '<provider>:<provider_place_id>'."""

    __tablename__ = "places"
    __table_args__ = (
        UniqueConstraint("provider", "provider_place_id"),
        CheckConstraint("rating IS NULL OR rating BETWEEN 0 AND 5", name="rating_range"),
        CheckConstraint("price_level IS NULL OR price_level BETWEEN 1 AND 4", name="price_level_range"),
        CheckConstraint("typical_visit_minutes BETWEEN 5 AND 600", name="visit_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(40))
    provider_place_id: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(120))
    # geography(Point, 4326): distances in metres via ST_Distance / ST_DWithin. GiST index is created.
    location: Mapped[object] = mapped_column(Geography(geometry_type="POINT", srid=4326))
    categories: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")
    opening_hours: Mapped[list | None] = mapped_column(JSONB)  # NULL = unknown
    rating: Mapped[float | None] = mapped_column(Float)
    rating_count: Mapped[int | None]
    price_level: Mapped[int | None] = mapped_column(SmallInteger)
    wheelchair_accessible: Mapped[bool | None]
    timezone: Mapped[str] = mapped_column(String(64), server_default="UTC")
    typical_visit_minutes: Mapped[int] = mapped_column(SmallInteger, server_default="60")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProviderSnapshotRow(Base):
    """Short-lived record of a provider call: which normalized results it returned and until when they are fresh."""

    __tablename__ = "provider_snapshots"
    __table_args__ = (
        UniqueConstraint("provider", "kind", "request_hash"),
        CheckConstraint("expires_at > fetched_at", name="ttl_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(40))
    kind: Mapped[str] = mapped_column(String(40))
    request_hash: Mapped[str] = mapped_column(String(64))
    request: Mapped[dict] = mapped_column(JSONB)
    result_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class RouteLegRow(Base):
    """Cached travel time between two places for one mode and provider."""

    __tablename__ = "route_legs"
    __table_args__ = (
        UniqueConstraint("provider", "mode", "origin_id", "destination_id"),
        CheckConstraint("mode IN ('walk', 'drive')", name="mode_valid"),
        CheckConstraint("duration_s >= 0 AND distance_m >= 0", name="non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(40))
    mode: Mapped[str] = mapped_column(String(8))
    origin_id: Mapped[str] = mapped_column(String(300))
    destination_id: Mapped[str] = mapped_column(String(300))
    duration_s: Mapped[int]
    distance_m: Mapped[int]
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ExpenseRow(TimestampMixin, Base):
    """What was bought and its total cost. Payer and shares are separate concepts."""

    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("char_length(currency) = 3", name="currency_iso"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    description: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Money)
    currency: Mapped[str] = mapped_column(String(3))
    payer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trip_members.id"), index=True)
    incurred_on: Mapped[date | None] = mapped_column(Date)

    shares: Mapped[list["ExpenseShareRow"]] = relationship(cascade="all, delete-orphan")


class ExpenseShareRow(Base):
    """Who economically owes what part of an expense."""

    __tablename__ = "expense_shares"
    __table_args__ = (CheckConstraint("amount >= 0", name="amount_non_negative"),)

    expense_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("expenses.id", ondelete="CASCADE"), primary_key=True)
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trip_members.id"), primary_key=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Money)


class TransferRow(TimestampMixin, Base):
    """Money one member sent another. Never counted as trip cost."""

    __tablename__ = "transfers"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("sender_id <> recipient_id", name="distinct_parties"),
        CheckConstraint("char_length(currency) = 3", name="currency_iso"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trip_members.id"))
    recipient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trip_members.id"))
    amount: Mapped[Decimal] = mapped_column(Money)
    currency: Mapped[str] = mapped_column(String(3))
    sent_on: Mapped[date | None] = mapped_column(Date)
