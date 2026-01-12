import unittest
from decimal import Decimal
from uuid import uuid4

from domain import (
    Order, OrderLine, Money, OrderStatus,
    EmptyOrderError, OrderAlreadyPaidError, OrderCannotBeModifiedError,
    InvalidOrderLineError
)


class TestMoneyValueObject(unittest.TestCase):
    """Тесты для Money value object"""

    def test_creation(self):
        """Тест создания денежного объекта"""
        money = Money(Decimal('100.50'), "USD")
        self.assertEqual(money.amount, Decimal('100.50'))
        self.assertEqual(money.currency, "USD")

    def test_negative_amount(self):
        """Тест: нельзя создать отрицательную сумму"""
        with self.assertRaises(ValueError):
            Money(Decimal('-10'))

    def test_addition(self):
        """Тест сложения денежных сумм"""
        m1 = Money(Decimal('50.25'))
        m2 = Money(Decimal('25.75'))
        result = m1 + m2
        self.assertEqual(result.amount, Decimal('76.00'))

    def test_multiplication(self):
        """Тест умножения на целое число"""
        money = Money(Decimal('10.99'))
        result = money * 3
        self.assertEqual(result.amount, Decimal('32.97'))

    def test_different_currencies(self):
        """Тест: нельзя складывать разные валюты"""
        usd = Money(Decimal('100'), "USD")
        eur = Money(Decimal('100'), "EUR")
        with self.assertRaises(ValueError):
            _ = usd + eur

    def test_equality(self):
        """Тест сравнения денежных объектов"""
        m1 = Money(Decimal('100.00'))
        m2 = Money(Decimal('100.00'))
        m3 = Money(Decimal('200.00'))
        self.assertEqual(m1, m2)
        self.assertNotEqual(m1, m3)


class TestOrderLine(unittest.TestCase):
    """Тесты для OrderLine"""

    def setUp(self):
        self.price = Money(Decimal('10.50'))
        self.product_id = uuid4()

    def test_creation(self):
        """Тест создания строки заказа"""
        line = OrderLine(self.product_id, "Test Product", self.price, 2)
        self.assertEqual(line.product_id, self.product_id)
        self.assertEqual(line.quantity, 2)
        self.assertEqual(line.subtotal.amount, Decimal('21.00'))

    def test_zero_quantity(self):
        """Тест: количество должно быть положительным"""
        with self.assertRaises(InvalidOrderLineError):
            OrderLine(self.product_id, "Test", self.price, 0)

    def test_negative_quantity(self):
        """Тест: количество не может быть отрицательным"""
        with self.assertRaises(InvalidOrderLineError):
            OrderLine(self.product_id, "Test", self.price, -1)

    def test_zero_price(self):
        """Тест: цена должна быть положительной"""
        with self.assertRaises(InvalidOrderLineError):
            OrderLine(self.product_id, "Test", Money(Decimal('0')), 1)


class TestOrderAggregate(unittest.TestCase):
    """Тесты для агрегата Order"""

    def setUp(self):
        self.order = Order()
        self.product1_id = uuid4()
        self.product2_id = uuid4()
        self.price1 = Money(Decimal('25.99'))
        self.price2 = Money(Decimal('9.99'))

    def test_initial_state(self):
        """Тест начального состояния заказа"""
        self.assertEqual(self.order.status, OrderStatus.PENDING)
        self.assertEqual(self.order.line_count, 0)
        self.assertEqual(self.order.total.amount, Decimal('0'))
        self.assertFalse(self.order.is_paid)
        self.assertIsNone(self.order.paid_at)

    def test_add_line(self):
        """Тест добавления строки в заказ"""
        self.order.add_line(self.product1_id, "Product 1", self.price1, 2)
        self.assertEqual(self.order.line_count, 1)
        self.assertEqual(self.order.lines[0].quantity, 2)

    def test_add_existing_product(self):
        """Тест добавления уже существующего товара"""
        self.order.add_line(self.product1_id, "Product 1", self.price1, 2)
        self.order.add_line(self.product1_id, "Product 1", self.price1, 3)
        self.assertEqual(self.order.line_count, 1)
        self.assertEqual(self.order.lines[0].quantity, 5)

    def test_remove_line(self):
        """Тест удаления строки"""
        self.order.add_line(self.product1_id, "Product 1", self.price1, 2)
        self.order.add_line(self.product2_id, "Product 2", self.price2, 1)

        self.order.remove_line(self.product1_id)
        self.assertEqual(self.order.line_count, 1)
        self.assertEqual(self.order.lines[0].product_id, self.product2_id)

    def test_update_quantity(self):
        """Тест обновления количества"""
        self.order.add_line(self.product1_id, "Product 1", self.price1, 2)
        self.order.update_quantity(self.product1_id, 5)
        self.assertEqual(self.order.lines[0].quantity, 5)

    def test_update_quantity_to_zero_removes(self):
        """Тест: обновление количества до 0 удаляет строку"""
        self.order.add_line(self.product1_id, "Product 1", self.price1, 2)
        self.order.update_quantity(self.product1_id, 0)
        self.assertEqual(self.order.line_count, 0)

    def test_clear_lines(self):
        """Тест очистки всех строк"""
        self.order.add_line(self.product1_id, "Product 1", self.price1, 2)
        self.order.add_line(self.product2_id, "Product 2", self.price2, 3)
        self.order.clear_lines()
        self.assertEqual(self.order.line_count, 0)

    def test_total_calculation(self):
        """Тест расчета итоговой суммы"""
        self.order.add_line(self.product1_id, "Product 1", self.price1, 2)  # 51.98
        self.order.add_line(self.product2_id, "Product 2", self.price2, 3)  # 29.97

        expected_total = Decimal('51.98') + Decimal('29.97')
        self.assertEqual(self.order.total.amount, expected_total)

    def test_pay_order(self):
        """Тест оплаты заказа"""
        self.order.add_line(self.product1_id, "Product 1", self.price1, 1)
        self.order.pay()

        self.assertEqual(self.order.status, OrderStatus.PAID)
        self.assertTrue(self.order.is_paid)
        self.assertIsNotNone(self.order.paid_at)

    def test_pay_empty_order(self):
        """Тест: нельзя оплатить пустой заказ"""
        with self.assertRaises(EmptyOrderError):
            self.order.pay()

    def test_double_payment(self):
        """Тест: нельзя оплатить заказ повторно"""
        self.order.add_line(self.product1_id, "Product 1", self.price1, 1)
        self.order.pay()

        with self.assertRaises(OrderAlreadyPaidError):
            self.order.pay()

    def test_modify_after_payment(self):
        """Тест: нельзя изменять оплаченный заказ"""
        self.order.add_line(self.product1_id, "Product 1", self.price1, 1)
        self.order.pay()

        # Проверяем все методы изменения
        with self.assertRaises(OrderCannotBeModifiedError):
            self.order.add_line(self.product2_id, "Product 2", self.price2, 1)

        with self.assertRaises(OrderCannotBeModifiedError):
            self.order.remove_line(self.product1_id)

        with self.assertRaises(OrderCannotBeModifiedError):
            self.order.update_quantity(self.product1_id, 2)

        with self.assertRaises(OrderCannotBeModifiedError):
            self.order.clear_lines()

    def test_cancel_order(self):
        """Тест отмены заказа"""
        self.order.add_line(self.product1_id, "Product 1", self.price1, 1)
        self.order.cancel()
        self.assertEqual(self.order.status, OrderStatus.CANCELLED)

    def test_cannot_cancel_paid_order(self):
        """Тест: нельзя отменить оплаченный заказ"""
        self.order.add_line(self.product1_id, "Product 1", self.price1, 1)
        self.order.pay()

        with self.assertRaises(OrderCannotBeModifiedError):
            self.order.cancel()


if __name__ == '__main__':
    unittest.main()