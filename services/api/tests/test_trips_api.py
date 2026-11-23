from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_create_trip_echoes_unsaved_trip(egypt_trip_create):
    resp = client.post("/v1/trips", json=egypt_trip_create)
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] and body["status"] == "draft"
    assert body["travellers"] == 2
    assert body["stops"][2]["leave_on"] == "2026-11-06"
    assert body["budget"]["total"] == {"amount": "2500.00", "currency": "GBP"}


def test_validation_error_uses_envelope(egypt_trip_create):
    resp = client.post("/v1/trips", json={**egypt_trip_create, "end_date": "2026-10-01"})
    assert resp.status_code == 422
    error = resp.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"] and {"loc", "msg", "type"} <= set(error["details"][0])


def test_unimplemented_routes_return_501_envelope():
    resp = client.get(f"/v1/trips/{uuid4()}")
    assert resp.status_code == 501
    assert resp.json()["error"]["code"] == "not_implemented"


def test_unknown_route_uses_envelope():
    resp = client.get("/nope")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_openapi_declares_m1_surface():
    paths = client.get("/openapi.json").json()["paths"]
    assert {"post", "get", "patch", "delete"} <= set(paths["/v1/trips/{trip_id}"]) | set(paths["/v1/trips"])
    for sub in ("members", "constraints", "bookings"):
        assert f"/v1/trips/{{trip_id}}/{sub}" in paths
