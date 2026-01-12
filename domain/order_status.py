from enum import Enum


class OrderStatus(Enum):
    """Статусы заказа"""
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"