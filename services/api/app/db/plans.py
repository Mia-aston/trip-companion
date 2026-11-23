"""Persistence for immutable plan versions (AI-002). Only this module touches plan rows."""

from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import ItineraryDayRow, ItineraryItemRow, PlanVersionRow
from app.domain.itinerary.plan import PlanDay, PlanItem
from app.domain.itinerary.validator import Violation
from app.domain.itinerary.versions import PlanDiff, PlanVersion

_VIOLATIONS = TypeAdapter(list[Violation])


def _to_domain(row: PlanVersionRow) -> PlanVersion:
    return PlanVersion(
        trip_id=row.trip_id,
        version=row.version,
        parent_version=row.parent_version,
        created_by=row.created_by,
        planner=row.planner,
        reason=row.reason,
        explanation=row.explanation,
        warnings=_VIOLATIONS.validate_python(row.warnings),
        diff=PlanDiff.model_validate(row.diff) if row.diff else None,
        created_at=row.created_at,
        days=[
            PlanDay(
                date=d.date,
                stop_seq=d.stop_seq,
                timezone=d.timezone,
                items=[
                    PlanItem(
                        item_key=i.item_key,
                        kind=i.kind,
                        title=i.title,
                        place_id=i.place_id,
                        booking_id=i.booking_id,
                        starts_at=i.starts_at,
                        ends_at=i.ends_at,
                        locked=i.locked,
                        weather_sensitive=i.weather_sensitive,
                        source=i.source,
                        why=i.why,
                    )
                    for i in d.items
                ],
            )
            for d in row.days
        ],
    )


class PlanRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def next_version(self, trip_id: UUID) -> int:
        current = self.session.scalar(select(func.max(PlanVersionRow.version)).where(PlanVersionRow.trip_id == trip_id))
        return (current or 0) + 1

    def add(self, plan: PlanVersion, capacities: dict | None = None, notes: dict | None = None) -> PlanVersion:
        row = PlanVersionRow(
            trip_id=plan.trip_id,
            version=plan.version,
            parent_version=plan.parent_version,
            created_by=plan.created_by.value,
            planner=plan.planner,
            reason=plan.reason,
            explanation=plan.explanation,
            warnings=[v.model_dump(mode="json") for v in plan.warnings],
            diff=plan.diff.model_dump(mode="json") if plan.diff else None,
            days=[
                ItineraryDayRow(
                    date=d.date,
                    stop_seq=d.stop_seq,
                    timezone=d.timezone,
                    capacity_minutes=(capacities or {}).get(d.date, 0),
                    notes=(notes or {}).get(d.date, []),
                    items=[
                        ItineraryItemRow(
                            position=pos,
                            **i.model_dump(exclude={"kind", "source"}),
                            kind=i.kind.value,
                            source=i.source.value,
                        )
                        for pos, i in enumerate(d.items)
                    ],
                )
                for d in plan.days
            ],
        )
        self.session.add(row)
        self.session.flush()
        return self.get(plan.trip_id, plan.version)

    def get(self, trip_id: UUID, version: int | None = None) -> PlanVersion | None:
        """A specific version, or the latest when `version` is None."""
        stmt = select(PlanVersionRow).where(PlanVersionRow.trip_id == trip_id)
        stmt = (
            stmt.where(PlanVersionRow.version == version) if version else stmt.order_by(PlanVersionRow.version.desc())
        )
        stmt = stmt.options(selectinload(PlanVersionRow.days).selectinload(ItineraryDayRow.items)).limit(1)
        row = self.session.scalars(stmt.execution_options(populate_existing=True)).first()
        return _to_domain(row) if row else None
