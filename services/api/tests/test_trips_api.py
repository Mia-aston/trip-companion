"""API tests that need no database. Persistence-backed API tests live in tests/db/test_trips_api.py."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_validation_error_uses_envelope(egypt_trip_create):
    resp = client.post("/v1/trips", json={**egypt_trip_create, "end_date": "2026-10-01"})
    assert resp.status_code == 422
    error = resp.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"] and {"loc", "msg", "type"} <= set(error["details"][0])


def test_bad_uuid_is_validation_error():
    assert client.get("/v1/trips/not-a-uuid").json()["error"]["code"] == "validation_error"


def test_unknown_route_uses_envelope():
    resp = client.get("/nope")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_openapi_declares_m1_surface():
    paths = client.get("/openapi.json").json()["paths"]
    assert {"post"} <= set(paths["/v1/trips"])
    assert {"get", "patch", "delete"} <= set(paths["/v1/trips/{trip_id}"])
    for sub in ("members", "constraints", "bookings"):
        assert "post" in paths[f"/v1/trips/{{trip_id}}/{sub}"]
        assert "delete" in paths[f"/v1/trips/{{trip_id}}/{sub}/{{{sub[:-1]}_id}}"]
