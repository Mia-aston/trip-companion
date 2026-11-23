from decimal import Decimal

import pytest

from app.domain.expenses.models import Currency, Expense, ExpenseShare, trip_cost


def _expense(amount: str, currency: Currency = Currency.GBP) -> Expense:
    return Expense(
        id="e",
        description="dinner",
        amount=Decimal(amount),
        currency=currency,
        payer_id="a",
        shares=(ExpenseShare("a", Decimal(amount) / 2), ExpenseShare("b", Decimal(amount) / 2)),
    )


def test_trip_cost_sums_expenses():
    assert trip_cost([_expense("10.50"), _expense("4.50")], currency=Currency.GBP) == Decimal("15.00")


def test_trip_cost_of_nothing_is_zero():
    assert trip_cost([], currency=Currency.GBP) == Decimal("0")


def test_trip_cost_refuses_mixed_currencies():
    with pytest.raises(ValueError):
        trip_cost([_expense("10"), _expense("10", Currency.EUR)], currency=Currency.GBP)
