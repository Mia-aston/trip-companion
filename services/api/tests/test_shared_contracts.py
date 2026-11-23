from datetime import UTC, datetime, time
from decimal import Decimal

import pytest
from pydantic import TypeAdapter, ValidationError

from app.domain.shared.models import GeoPoint, Money, Provenance, TimeWindow, TimeZoneName


def test_money_serializes_amount_as_string():
    assert Money(amount="128.62", currency="EUR").model_dump(mode="json") == {"amount": "128.62", "currency": "EUR"}


def test_money_keeps_decimal_exactly():
    assert Money(amount="0.10", currency="GBP").amount + Money(amount="0.20", currency="GBP").amount == Decimal("0.30")


@pytest.mark.parametrize(
    "payload",
    [
        {"amount": "1.234", "currency": "GBP"},
        {"amount": "1", "currency": "gbp"},
        {"amount": "1", "currency": "POUND"},
        {"amount": "1", "currency": "GBP", "extra": True},
    ],
    ids=["three-decimals", "lowercase-currency", "long-currency", "unknown-field"],
)
def test_money_rejects_invalid(payload):
    with pytest.raises(ValidationError):
        Money.model_validate(payload)


def test_time_window_must_be_ordered():
    assert TimeWindow(start=time(8), end=time(21))
    with pytest.raises(ValidationError):
        TimeWindow(start=time(21), end=time(8))


def test_provider_provenance_requires_timestamp():
    with pytest.raises(ValidationError):
        Provenance(source="provider", provider="mock")
    assert Provenance(source="provider", provider="mock", fetched_at=datetime.now(UTC))
    assert Provenance(source="user")


def test_provenance_rejects_naive_datetime():
    with pytest.raises(ValidationError):
        Provenance(source="provider", provider="mock", fetched_at=datetime(2026, 11, 1, 9))


def test_timezone_must_be_iana():
    adapter = TypeAdapter(TimeZoneName)
    assert adapter.validate_python("Africa/Cairo") == "Africa/Cairo"
    with pytest.raises(ValidationError):
        adapter.validate_python("Cairo/Egypt")


def test_geopoint_ranges():
    with pytest.raises(ValidationError):
        GeoPoint(lat=91, lon=0)


def test_datetimes_are_normalized_to_utc():
    p = Provenance(source="provider", provider="mock", fetched_at="2026-11-06T22:30:00+02:00")
    assert p.fetched_at == datetime(2026, 11, 6, 20, 30, tzinfo=UTC)
    assert p.model_dump(mode="json")["fetched_at"] == "2026-11-06T20:30:00Z"
