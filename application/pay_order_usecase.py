from typing import Dict, Any
from uuid import UUID

from domain.order_aggregate import Order
from domain.domain_exceptions import DomainException
from .interfaces import OrderRepository, PaymentGateway


class PaymentResult:
    """Результат операции оплаты"""

    def __init__(self, success: bool, order_id: UUID = None,
                 transaction_id: str = None, error: str = None):
        self.success = success
        self.order_id = order_id
        self.transaction_id = transaction_id
        self.error = error

    def __bool__(self) -> bool:
        return self.success

    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать результат в словарь"""
        return {
            'success': self.success,
            'order_id': str(self.order_id) if self.order_id else None,
            'transaction_id': self.transaction_id,
            'error': self.error
        }


class PayOrderUseCase:
    """Use case для оплаты заказа"""

    def __init__(self, order_repository: OrderRepository,
                 payment_gateway: PaymentGateway):
        self.order_repository = order_repository
        self.payment_gateway = payment_gateway

    def execute(self, order_id: UUID) -> PaymentResult:
        """
        Выполнить оплату заказа

        Steps:
        1. Загрузить заказ через OrderRepository
        2. Выполнить доменную операцию оплаты
        3. Вызвать платеж через PaymentGateway
        4. Сохранить заказ
        5. Вернуть результат оплаты
        """
        try:
            # 1. Загружаем заказ
            order = self.order_repository.get_by_id(order_id)
            if order is None:
                return PaymentResult(
                    success=False,
                    order_id=order_id,
                    error=f"Order {order_id} not found"
                )

            # 2. Выполняем доменную операцию оплаты
            order.pay()

            # 3. Вызываем платежный шлюз
            transaction_id = self.payment_gateway.charge(order_id, order.total)

            # 4. Сохраняем заказ
            self.order_repository.save(order)

            return PaymentResult(
                success=True,
                order_id=order_id,
                transaction_id=transaction_id
            )

        except DomainException as e:
            return PaymentResult(
                success=False,
                order_id=order_id,
                error=str(e)
            )
        except Exception as e:
            # Логируем ошибку (в реальном приложении)
            # logger.error(f"Payment failed for order {order_id}: {e}")
            return PaymentResult(
                success=False,
                order_id=order_id,
                error=f"Payment processing error: {str(e)}"
            )