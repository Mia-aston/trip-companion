"""Flight offer snapshots (FLIGHT-002, A-24). Only this module touches transport_options rows."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import TransportOptionRow
from app.domain.flights.models import Direction, FlightOffer

_COMPUTED = {"stops", "departs_at", "arrives_at", "duration_minutes"}


def _dump(offer: FlightOffer) -> dict:
    return offer.model_dump(mode="json", exclude=_COMPUTED)


class FlightSnapshots:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(self, trip_id: UUID, search_id: UUID, direction: Direction, offers: list[FlightOffer]) -> None:
        for o in offers:
            self.session.add(
                TransportOptionRow(
                    trip_id=trip_id,
                    search_id=search_id,
                    direction=direction.value,
                    provider=o.provider,
                    offer_id=o.id,
                    offer=_dump(o),
                    total_amount=o.total.amount,
                    currency=o.total.currency,
                    stops=o.stops,
                    departs_at=o.departs_at,
                    arrives_at=o.arrives_at,
                    fetched_at=o.provenance.fetched_at,
                    expires_at=o.expires_at,
                )
            )
        self.session.flush()

    def latest(self, trip_id: UUID, offer_id: str) -> tuple[Direction, FlightOffer, TransportOptionRow] | None:
        """Most recent snapshot of an offer for this trip (used by select, FLIGHT-004)."""
        row = self.session.scalars(
            select(TransportOptionRow)
            .where(TransportOptionRow.trip_id == trip_id, TransportOptionRow.offer_id == offer_id)
            .order_by(TransportOptionRow.fetched_at.desc())
            .limit(1)
        ).first()
        if row is None:
            return None
        offer = FlightOffer.model_validate(row.offer)
        # the column is the source of truth for expiry (queryable; can be shortened by the provider later)
        return Direction(row.direction), offer.model_copy(update={"expires_at": row.expires_at}), row
