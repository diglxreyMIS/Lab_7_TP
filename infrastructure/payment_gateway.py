import random
import string
from datetime import datetime
from typing import List, Dict, Any
from uuid import UUID

from domain.money import Money
from application.interfaces import PaymentGateway


class TransactionRecord:
    """Запись о транзакции"""

    def __init__(self, order_id: UUID, amount: Money, transaction_id: str):
        self.order_id = order_id
        self.amount = amount
        self.transaction_id = transaction_id
        self.timestamp = datetime.now()
        self.status = "completed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'order_id': str(self.order_id),
            'amount': str(self.amount),
            'transaction_id': self.transaction_id,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status
        }


class FakePaymentGateway(PaymentGateway):
    """Fake реализация платежного шлюза"""

    def __init__(self, success_rate: float = 1.0,
                 simulate_failure: bool = False):
        """
        Args:
            success_rate: вероятность успешного платежа (0.0-1.0)
            simulate_failure: имитировать ли сбои платежа
        """
        self.success_rate = success_rate
        self.simulate_failure = simulate_failure
        self.transactions: List[TransactionRecord] = []
        self.failures_count = 0

    def _generate_transaction_id(self) -> str:
        """Сгенерировать ID транзакции"""
        prefix = "TXN"
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        return f"{prefix}_{random_chars}"

    def charge(self, order_id: UUID, amount: Money) -> str:
        """Имитация платежа"""
        # Имитация случайного отказа платежного шлюза
        if self.simulate_failure and random.random() > self.success_rate:
            self.failures_count += 1
            raise Exception(f"Payment gateway declined transaction for order {order_id}")

        # Генерация ID транзакции
        transaction_id = self._generate_transaction_id()

        # Создание записи о транзакции
        transaction = TransactionRecord(order_id, amount, transaction_id)
        self.transactions.append(transaction)

        return transaction_id

    def get_transaction_history(self) -> List[Dict[str, Any]]:
        """Получить историю транзакций"""
        return [tx.to_dict() for tx in self.transactions]

    def get_transaction_by_order(self, order_id: UUID) -> Optional[Dict[str, Any]]:
        """Найти транзакцию по ID заказа"""
        for tx in self.transactions:
            if tx.order_id == order_id:
                return tx.to_dict()
        return None

    def clear_history(self) -> None:
        """Очистить историю транзакций (для тестов)"""
        self.transactions.clear()
        self.failures_count = 0