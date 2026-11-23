"""Translate between ORM rows and domain objects. Only this layer touches rows.

KNOWN GAP: TripRepository targets migration 0001 (single `travellers` column) and does not
match the CORE-001 Trip contract yet. CORE-002 adds migration 0002 and rewrites this mapping.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import TripRow
from app.domain.trips.models import Pace, Trip, TripCreate


def _to_domain(row: TripRow) -> Trip:
    return Trip(
        id=row.id,
        origin=row.origin,
        destination=row.destination,
        start_date=row.start_date,
        end_date=row.end_date,
        travellers=row.travellers,
        interests=list(row.interests),
        pace=Pace(row.pace),
    )


class TripRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, payload: TripCreate) -> Trip:
        row = TripRow(**payload.model_dump(mode="python"))
        self.session.add(row)
        self.session.flush()
        return _to_domain(row)

    def get(self, trip_id: UUID) -> Trip | None:
        row = self.session.get(TripRow, trip_id)
        return _to_domain(row) if row else None
