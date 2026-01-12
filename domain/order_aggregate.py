from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List
from uuid import UUID, uuid4

from .domain_exceptions import (
    EmptyOrderError,
    OrderAlreadyPaidError,
    OrderCannotBeModifiedError,
    InvalidOrderLineError
)
from .money import Money
from .order_status import OrderStatus


@dataclass
class OrderLine:
    """Часть агрегата Order - Value Object"""
    product_id: UUID
    product_name: str
    price: Money
    quantity: int

    def __post_init__(self):
        if self.quantity <= 0:
            raise InvalidOrderLineError("Quantity must be positive")
        if self.price.amount <= Decimal('0'):
            raise InvalidOrderLineError("Price must be positive")

    @property
    def subtotal(self) -> Money:
        return self.price * self.quantity

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OrderLine):
            return False
        return (self.product_id == other.product_id and
                self.product_name == other.product_name and
                self.price == other.price and
                self.quantity == other.quantity)


@dataclass
class Order:
    """Агрегат заказа - Entity"""
    id: UUID = field(default_factory=uuid4)
    customer_id: UUID = field(default_factory=uuid4)
    lines: List[OrderLine] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    paid_at: datetime = None

    def __post_init__(self):
        self._version = 0  # Для оптимистичной блокировки

    def add_line(self, product_id: UUID, product_name: str, price: Money, quantity: int) -> None:
        """Добавить строку в заказ"""
        self._check_modifiable()

        # Проверяем, нет ли уже такого товара в заказе
        for line in self.lines:
            if line.product_id == product_id:
                line.quantity += quantity
                self._version += 1
                return

        # Добавляем новую строку
        line = OrderLine(
            product_id=product_id,
            product_name=product_name,
            price=price,
            quantity=quantity
        )
        self.lines.append(line)
        self._version += 1

    def remove_line(self, product_id: UUID) -> None:
        """Удалить строку из заказа"""
        self._check_modifiable()

        initial_length = len(self.lines)
        self.lines = [line for line in self.lines if line.product_id != product_id]

        if len(self.lines) != initial_length:
            self._version += 1

    def update_quantity(self, product_id: UUID, quantity: int) -> None:
        """Обновить количество товара"""
        self._check_modifiable()

        for line in self.lines:
            if line.product_id == product_id:
                if quantity <= 0:
                    self.remove_line(product_id)
                else:
                    line.quantity = quantity
                self._version += 1
                return

        raise ValueError(f"Product {product_id} not found in order")

    def clear_lines(self) -> None:
        """Очистить все строки заказа"""
        self._check_modifiable()
        self.lines.clear()
        self._version += 1

    def _check_modifiable(self) -> None:
        """Проверить, можно ли изменять заказ"""
        if self.status == OrderStatus.PAID:
            raise OrderCannotBeModifiedError("Cannot modify paid order")

    @property
    def total(self) -> Money:
        """Итоговая сумма заказа"""
        if not self.lines:
            return Money(Decimal('0'))

        total = Money(Decimal('0'), self.lines[0].price.currency)
        for line in self.lines:
            total = total + line.subtotal
        return total

    def pay(self) -> None:
        """Оплатить заказ - основная доменная операция"""
        # Инвариант 1: нельзя оплатить пустой заказ
        if not self.lines:
            raise EmptyOrderError("Cannot pay empty order")

        # Инвариант 2: нельзя оплатить заказ повторно
        if self.status == OrderStatus.PAID:
            raise OrderAlreadyPaidError("Order is already paid")

        # Инвариант 3: итоговая сумма равна сумме строк
        # (автоматически проверяется через свойство total)

        self.status = OrderStatus.PAID
        self.paid_at = datetime.now()
        self._version += 1

    def cancel(self) -> None:
        """Отменить заказ"""
        self._check_modifiable()
        self.status = OrderStatus.CANCELLED
        self._version += 1

    @property
    def is_paid(self) -> bool:
        return self.status == OrderStatus.PAID

    @property
    def line_count(self) -> int:
        return len(self.lines)