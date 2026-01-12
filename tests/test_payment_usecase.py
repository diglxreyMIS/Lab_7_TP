import unittest
from decimal import Decimal
from uuid import uuid4

from domain import Order, Money
from application import PayOrderUseCase, PaymentResult
from infrastructure import InMemoryOrderRepository, FakePaymentGateway


class TestPayOrderUseCase(unittest.TestCase):
    """Тесты для use case оплаты заказа"""

    def setUp(self):
        self.order_repository = InMemoryOrderRepository()
        self.payment_gateway = FakePaymentGateway(success_rate=1.0)
        self.use_case = PayOrderUseCase(self.order_repository, self.payment_gateway)

        # Создаем тестовый заказ
        self.order = Order()
        self.product1_id = uuid4()
        self.product2_id = uuid4()
        self.order.add_line(self.product1_id, "Laptop", Money(Decimal('999.99')), 1)
        self.order.add_line(self.product2_id, "Mouse", Money(Decimal('29.99')), 2)
        self.order_repository.save(self.order)

    def tearDown(self):
        self.order_repository.clear()
        self.payment_gateway.clear_history()

    def test_successful_payment(self):
        """Тест успешной оплаты корректного заказа"""
        result = self.use_case.execute(self.order.id)

        self.assertTrue(result.success)
        self.assertEqual(result.order_id, self.order.id)
        self.assertIsNotNone(result.transaction_id)
        self.assertIsNone(result.error)

        # Проверяем, что заказ обновился в репозитории
        updated_order = self.order_repository.get_by_id(self.order.id)
        self.assertTrue(updated_order.is_paid)

        # Проверяем, что транзакция записана в платежном шлюзе
        transactions = self.payment_gateway.get_transaction_history()
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0]['order_id'], str(self.order.id))

    def test_payment_empty_order(self):
        """Тест ошибки при оплате пустого заказа"""
        empty_order = Order()
        self.order_repository.save(empty_order)

        result = self.use_case.execute(empty_order.id)

        self.assertFalse(result.success)
        self.assertEqual(result.order_id, empty_order.id)
        self.assertIsNone(result.transaction_id)
        self.assertIsNotNone(result.error)
        self.assertIn("Cannot pay empty order", result.error)

    def test_double_payment_error(self):
        """Тест ошибки при повторной оплате"""
        # Первая оплата (успешная)
        result1 = self.use_case.execute(self.order.id)
        self.assertTrue(result1.success)

        # Вторая попытка оплаты
        result2 = self.use_case.execute(self.order.id)

        self.assertFalse(result2.success)
        self.assertEqual(result2.order_id, self.order.id)
        self.assertIn("already paid", result2.error.lower())

    def test_order_not_found(self):
        """Тест оплаты несуществующего заказа"""
        non_existent_id = uuid4()
        result = self.use_case.execute(non_existent_id)

        self.assertFalse(result.success)
        self.assertEqual(result.order_id, non_existent_id)
        self.assertIn("not found", result.error.lower())

    def test_cannot_modify_after_payment(self):
        """Тест невозможности изменения заказа после оплаты"""
        # Оплачиваем заказ
        self.use_case.execute(self.order.id)
        paid_order = self.order_repository.get_by_id(self.order.id)

        # Пытаемся изменить оплаченный заказ
        with self.assertRaises(Exception):
            paid_order.add_line(uuid4(), "Keyboard", Money(Decimal('49.99')), 1)

    def test_correct_total_in_payment(self):
        """Тест корректного расчета итоговой суммы при платеже"""
        # Рассчитываем ожидаемую сумму
        expected_total = Decimal('999.99') + (Decimal('29.99') * 2)

        # Выполняем оплату
        result = self.use_case.execute(self.order.id)

        # Проверяем, что в платежный шлюз передана правильная сумма
        transactions = self.payment_gateway.get_transaction_history()
        transaction = transactions[0]

        # Извлекаем сумму из строки (т.к. она хранится как строка)
        amount_str = transaction['amount'].split()[1]  # "USD 1059.97"
        paid_amount = Decimal(amount_str)

        self.assertEqual(paid_amount, expected_total)

    def test_payment_gateway_failure(self):
        """Тест обработки сбоя платежного шлюза"""
        # Создаем шлюз с имитацией сбоев
        failing_gateway = FakePaymentGateway(success_rate=0.0, simulate_failure=True)
        use_case = PayOrderUseCase(self.order_repository, failing_gateway)

        result = use_case.execute(self.order.id)

        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)
        self.assertIn("error", result.error.lower())

        # Заказ не должен быть оплачен при сбое платежного шлюза
        order = self.order_repository.get_by_id(self.order.id)
        self.assertFalse(order.is_paid)

    def test_payment_result_to_dict(self):
        """Тест преобразования результата в словарь"""
        result = PaymentResult(
            success=True,
            order_id=self.order.id,
            transaction_id="TXN_123456",
            error=None
        )

        result_dict = result.to_dict()

        self.assertEqual(result_dict['success'], True)
        self.assertEqual(result_dict['order_id'], str(self.order.id))
        self.assertEqual(result_dict['transaction_id'], "TXN_123456")
        self.assertIsNone(result_dict['error'])

    def test_order_id_preserved_in_failure(self):
        """Тест сохранения ID заказа при неудачной оплате"""
        empty_order = Order()
        self.order_repository.save(empty_order)

        result = self.use_case.execute(empty_order.id)

        self.assertFalse(result.success)
        self.assertEqual(result.order_id, empty_order.id)


if __name__ == '__main__':
    unittest.main()