from abc import ABC, abstractmethod
from typing import Dict

class Currency(ABC):
    """Абстрактный базовый класс для валют"""
    
    def __init__(self, name: str, code: str):
        self._validate_code(code)
        self._validate_name(name)
        
        self._name = name
        self._code = code.upper()
    
    def _validate_code(self, code: str):
        """Валидация кода валюты"""
        if not isinstance(code, str):
            raise ValueError("Код валюты должен быть строкой")
        if not 2 <= len(code) <= 5:
            raise ValueError("Код валюты должен содержать от 2 до 5 символов")
        if not code.isalpha():
            raise ValueError("Код валюты должен содержать только буквы")
        if ' ' in code:
            raise ValueError("Код валюты не должен содержать пробелы")
    
    def _validate_name(self, name: str):
        """Валидация имени валюты"""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Имя валюты не может быть пустым")
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def code(self) -> str:
        return self._code
    
    @abstractmethod
    def get_display_info(self) -> str:
        """Строковое представление для UI/логов"""
        pass
    
    def __str__(self):
        return self.get_display_info()
    
    def __eq__(self, other):
        if not isinstance(other, Currency):
            return False
        return self.code == other.code

class FiatCurrency(Currency):
    """Фиатная валюта"""
    
    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)
        self._issuing_country = issuing_country
    
    @property
    def issuing_country(self) -> str:
        return self._issuing_country
    
    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"

class CryptoCurrency(Currency):
    """Криптовалюта"""
    
    def __init__(self, name: str, code: str, algorithm: str, market_cap: float = 0.0):
        super().__init__(name, code)
        self._algorithm = algorithm
        self._market_cap = market_cap
    
    @property
    def algorithm(self) -> str:
        return self._algorithm
    
    @property
    def market_cap(self) -> float:
        return self._market_cap
    
    def get_display_info(self) -> str:
        mcap_str = f"{self.market_cap:.2e}" if self.market_cap > 1e6 else f"{self.market_cap:,.2f}"
        return f"[CRYPTO] {self.code} — {self.name} (Algo: {self.algorithm}, MCAP: {mcap_str})"

# Реестр валют
_currency_registry: Dict[str, Currency] = {}

def register_currency(currency: Currency):
    """Регистрирует валюту в реестре"""
    _currency_registry[currency.code] = currency

def get_currency(code: str) -> Currency:
    """Фабричный метод для получения валюты по коду"""
    from .exceptions import CurrencyNotFoundError
    
    code = code.upper()
    if code not in _currency_registry:
        raise CurrencyNotFoundError(code)
    return _currency_registry[code]

def get_supported_currencies() -> Dict[str, Currency]:
    """Возвращает копию реестра поддерживаемых валют"""
    return _currency_registry.copy()

# Инициализация реестра при импорте
def _initialize_currencies():
    """Инициализирует базовый набор валют"""
    register_currency(FiatCurrency("US Dollar", "USD", "United States"))
    register_currency(FiatCurrency("Euro", "EUR", "Eurozone"))
    register_currency(FiatCurrency("Russian Ruble", "RUB", "Russia"))
    register_currency(CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12))
    register_currency(CryptoCurrency("Ethereum", "ETH", "Ethash", 4.5e11))

_initialize_currencies()