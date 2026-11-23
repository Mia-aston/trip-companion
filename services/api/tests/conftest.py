import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def egypt_trip_create() -> dict:
    """Egypt golden scenario TripCreate payload (docs/TESTING.md, A-06)."""
    return json.loads((FIXTURES / "egypt" / "trip_create.json").read_text())
