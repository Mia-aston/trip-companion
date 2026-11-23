"""Persistence schema (SQLAlchemy ORM).

ORM rows stay inside the persistence layer. Other modules exchange typed domain
objects (see `app/db/repositories.py`), never these classes.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from geoalchemy2 import Geography
from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

Money = Numeric(14, 2)

# References to trip_members use the default NO ACTION (checked at end of statement), not RESTRICT:
# deleting a member who paid/owes is refused, but deleting a whole trip cascades through members,
# expenses and transfers in one statement.


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TripRow(TimestampMixin, Base):
    __tablename__ = "trips"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="dates_ordered"),
        CheckConstraint("travellers BETWEEN 1 AND 20", name="travellers_range"),
        CheckConstraint("pace IN ('relaxed', 'balanced', 'packed')", name="pace_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    origin: Mapped[str] = mapped_column(String(120))
    destination: Mapped[str] = mapped_column(String(120))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    travellers: Mapped[int] = mapped_column(default=1)
    interests: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")
    pace: Mapped[str] = mapped_column(String(16), default="balanced")

    members: Mapped[list["TripMemberRow"]] = relationship(
        back_populates="trip", cascade="all, delete-orphan", passive_deletes=True
    )


class TripMemberRow(TimestampMixin, Base):
    __tablename__ = "trip_members"
    __table_args__ = (UniqueConstraint("trip_id", "display_name"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    display_name: Mapped[str] = mapped_column(String(80))

    trip: Mapped[TripRow] = relationship(back_populates="members")


class PlaceRow(TimestampMixin, Base):
    """Normalized place cache. `provider` + `provider_place_id` identify the source record."""

    __tablename__ = "places"
    __table_args__ = (UniqueConstraint("provider", "provider_place_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(40))
    provider_place_id: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    # geography(Point, 4326): distances in metres via ST_Distance / ST_DWithin. GiST index is created.
    location: Mapped[object] = mapped_column(Geography(geometry_type="POINT", srid=4326))
    categories: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")


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
