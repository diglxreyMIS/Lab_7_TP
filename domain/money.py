from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Money:
    """Value Object для денежных сумм"""
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self):
        if self.amount < Decimal('0'):
            raise ValueError("Amount cannot be negative")

    def __add__(self, other: 'Money') -> 'Money':
        if not isinstance(other, Money):
            raise TypeError("Can only add Money to Money")
        if self.currency != other.currency:
            raise ValueError(f"Cannot add different currencies: {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)

    def __mul__(self, quantity: int) -> 'Money':
        if not isinstance(quantity, int):
            raise TypeError("Can only multiply Money by integer")
        return Money(self.amount * Decimal(quantity), self.currency)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency == other.currency

    def __str__(self) -> str:
        return f"{self.currency} {self.amount:.2f}"