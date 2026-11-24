"""Seed the Egypt golden-scenario trip (CORE-004) into DATABASE_URL.

Usage:  python scripts/seed_egypt.py            # create if missing, print the trip id
        python scripts/seed_egypt.py --reset    # delete existing Egypt seed trips and recreate

Idempotent: a trip with the fixture's title and start date is treated as the seed.
"""

import json
import sys
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.models import TripRow  # noqa: E402
from app.db.repositories import TripRepository  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.domain.trips.models import TripCreate  # noqa: E402

# Stable id so the demo URL never changes: http://localhost:3000/trips/<DEMO_TRIP_ID>
DEMO_TRIP_ID = uuid5(NAMESPACE_URL, "trip-companion:demo:egypt")
FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "egypt" / "trip_create.json"


def egypt_payload() -> TripCreate:
    return TripCreate.model_validate(json.loads(FIXTURE.read_text()))


def seed(session: Session, *, reset: bool = False) -> tuple[UUID, bool]:
    """Return (trip_id, created). Does not commit."""
    payload = egypt_payload()
    existing = session.scalars(
        select(TripRow.id).where(
            (TripRow.id == DEMO_TRIP_ID)
            | ((TripRow.title == payload.title) & (TripRow.start_date == payload.start_date))
        )
    ).all()
    repo = TripRepository(session)
    if existing and not reset:
        return existing[0], False
    if DEMO_TRIP_ID in existing and not reset:
        return DEMO_TRIP_ID, False
    for trip_id in existing:
        repo.delete(trip_id)
    session.flush()
    return repo.add(payload, trip_id=DEMO_TRIP_ID).id, True


def main() -> int:
    with Session(get_engine()) as session:
        trip_id, created = seed(session, reset="--reset" in sys.argv)
        session.commit()
    print(f"{'created' if created else 'exists'} {trip_id}")
    print(f"Egypt demo trip: http://localhost:3000/trips/{trip_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
