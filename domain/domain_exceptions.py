class DomainException(Exception):
    """Базовое исключение доменного слоя"""
    pass


class EmptyOrderError(DomainException):
    """Ошибка при оплате пустого заказа"""
    pass


class OrderAlreadyPaidError(DomainException):
    """Ошибка при повторной оплате"""
    pass


class OrderCannotBeModifiedError(DomainException):
    """Ошибка при изменении оплаченного заказа"""
    pass


class InvalidOrderLineError(DomainException):
    """Ошибка в строке заказа"""
    pass