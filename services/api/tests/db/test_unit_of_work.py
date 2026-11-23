"""The real get_session dependency commits on success and rolls back on errors (no test override)."""

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import session as db_session
from app.main import app
from tests.db.conftest import TEST_DATABASE_URL


@pytest.fixture
def real_client(engine, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    for cached in (get_settings, db_session.get_engine, db_session._factory):
        cached.cache_clear()
    yield TestClient(app)
    for cached in (get_settings, db_session.get_engine, db_session._factory):
        cached.cache_clear()


def test_commit_on_success_and_nothing_left_after_delete(real_client, egypt_trip_create):
    trip = real_client.post("/v1/trips", json=egypt_trip_create).json()
    assert real_client.get(f"/v1/trips/{trip['id']}").status_code == 200  # visible from a new session
    assert real_client.delete(f"/v1/trips/{trip['id']}").status_code == 204
    assert real_client.get(f"/v1/trips/{trip['id']}").status_code == 404


def test_rollback_on_conflict(real_client, egypt_trip_create):
    trip = real_client.post("/v1/trips", json=egypt_trip_create).json()
    try:
        resp = real_client.post(f"/v1/trips/{trip['id']}/members", json={"display_name": "MIA"})
        assert resp.status_code == 409
        assert len(real_client.get(f"/v1/trips/{trip['id']}").json()["members"]) == 2
    finally:
        real_client.delete(f"/v1/trips/{trip['id']}")
