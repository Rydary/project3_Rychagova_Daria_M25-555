class ValutaTradeError(Exception):
    """Базовое исключение для торговой платформы"""
    pass

class InsufficientFundsError(ValutaTradeError):
    """Недостаточно средств"""
    
    def __init__(self, available: float, required: float, code: str):
        self.available = available
        self.required = required
        self.code = code
        super().__init__(f"Недостаточно средств: доступно {available} {code}, требуется {required} {code}")

class CurrencyNotFoundError(ValutaTradeError):
    """Неизвестная валюта"""
    
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")

class ApiRequestError(ValutaTradeError):
    """Ошибка внешнего API"""
    
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")

class ValidationError(ValutaTradeError):
    """Ошибка валидации данных"""
    pass

class AuthenticationError(ValutaTradeError):
    """Ошибка аутентификации"""
    pass