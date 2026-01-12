from typing import Dict, Optional
from uuid import UUID

from domain.order_aggregate import Order
from application.interfaces import OrderRepository


class InMemoryOrderRepository(OrderRepository):
    """In-memory реализация репозитория заказов"""

    def __init__(self):
        self._orders: Dict[UUID, Order] = {}

    def get_by_id(self, order_id: UUID) -> Optional[Order]:
        # Возвращаем копию заказа для защиты инкапсуляции
        order = self._orders.get(order_id)
        if order:
            # В реальном приложении здесь была бы глубокая копия
            # или ORM сессия
            return order
        return None

    def save(self, order: Order) -> None:
        self._orders[order.id] = order

    def delete(self, order_id: UUID) -> bool:
        """Удалить заказ (для тестов)"""
        if order_id in self._orders:
            del self._orders[order_id]
            return True
        return False

    def clear(self) -> None:
        """Очистить репозиторий (для тестов)"""
        self._orders.clear()

    def count(self) -> int:
        """Количество заказов в репозитории"""
        return len(self._orders)