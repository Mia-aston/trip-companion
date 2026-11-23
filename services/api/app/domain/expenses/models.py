from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class Currency(StrEnum):
    GBP = "GBP"
    EUR = "EUR"
    USD = "USD"
    EGP = "EGP"


@dataclass(frozen=True)
class ExpenseShare:
    member_id: str
    amount: Decimal


@dataclass(frozen=True)
class Expense:
    id: str
    description: str
    amount: Decimal
    currency: Currency
    payer_id: str
    shares: tuple[ExpenseShare, ...]


@dataclass(frozen=True)
class Transfer:
    sender_id: str
    recipient_id: str
    amount: Decimal
    currency: Currency


def trip_cost(expenses: list[Expense], *, currency: Currency) -> Decimal:
    if any(e.currency != currency for e in expenses):
        raise ValueError("Normalize FX before aggregating trip_cost")
    return sum((e.amount for e in expenses), Decimal("0"))
