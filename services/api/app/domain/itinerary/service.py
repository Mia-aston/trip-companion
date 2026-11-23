from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CandidateStop:
    place_id: str
    name: str
    opens_at: datetime | None
    closes_at: datetime | None
    duration_minutes: int
    interest_score: float


@dataclass(frozen=True)
class ScheduledStop:
    place_id: str
    name: str
    start: datetime
    end: datetime


def rank_candidates(candidates: list[CandidateStop]) -> list[CandidateStop]:
    """Deterministic baseline. Route/opening feasibility is added before LLM composition."""
    return sorted(candidates, key=lambda item: item.interest_score, reverse=True)
