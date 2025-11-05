import hashlib
from datetime import datetime
import secrets

class User:
    def __init__(self, user_id: int, username: str, password: str, registration_date: datetime = None):
        self._user_id = user_id
        self._username = username
        self._salt = secrets.token_hex(16)  # Генерируем случайную соль
        self._hashed_password = self._hash_password(password, self._salt)
        self._registration_date = registration_date or datetime.now()
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Хеширует пароль с солью"""
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    # Геттеры
    @property
    def user_id(self) -> int:
        return self._user_id
    
    @property
    def username(self) -> str:
        return self._username
    
    @username.setter
    def username(self, value: str):
        if not value or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value
    
    @property
    def registration_date(self) -> datetime:
        return self._registration_date
    
    # Методы класса
    def get_user_info(self) -> dict:
        """Возвращает информацию о пользователе (без пароля)"""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def change_password(self, new_password: str):
        """Изменяет пароль пользователя"""
        if len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")
        
        # Генерируем новую соль и хешируем пароль
        self._salt = secrets.token_hex(16)
        self._hashed_password = self._hash_password(new_password, self._salt)
    
    def verify_password(self, password: str) -> bool:
        """Проверяет введённый пароль на совпадение"""
        hashed_input = self._hash_password(password, self._salt)
        return hashed_input == self._hashed_password
    
    def __str__(self):
        return f"User(id={self._user_id}, username='{self._username}')"
        

class Wallet:
    def __init__(self, currency_code: str, balance: float = 0.0):
        self.currency_code = currency_code
        self._balance = balance
    
    @property
    def balance(self) -> float:
        """Геттер для баланса"""
        return self._balance
    
    @balance.setter
    def balance(self, value: float):
        """Сеттер для баланса с проверками"""
        if not isinstance(value, (int, float)):
            raise TypeError("Баланс должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(value)
    
    def deposit(self, amount: float):
        """Пополнение баланса"""
        if not isinstance(amount, (int, float)):
            raise TypeError("Сумма должна быть числом")
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительной")
        
        self.balance += amount
    
    def withdraw(self, amount: float):
        """Снятие средств"""
        if not isinstance(amount, (int, float)):
            raise TypeError("Сумма должна быть числом")
        if amount <= 0:
            raise ValueError("Сумма снятия должна быть положительной")
        if amount > self.balance:
            raise ValueError("Недостаточно средств на балансе")
        
        self.balance -= amount
    
    def get_balance_info(self) -> dict:
        """Вывод информации о текущем балансе"""
        return {
            "currency_code": self.currency_code,
            "balance": self.balance
        }
    
    def to_dict(self) -> dict:
        """Для сериализации в JSON"""
        return self.get_balance_info()
    
    def __str__(self):
        return f"Wallet({self.currency_code}: {self.balance})"
    
    
class Portfolio:
    def __init__(self, user_id: int, user: 'User' = None):
        self._user_id = user_id
        self._user = user
        self._wallets: dict[str, Wallet] = {}
    
    @property
    def user(self) -> 'User':
        """Геттер для пользователя"""
        return self._user
    
    @property
    def wallets(self) -> dict:
        """Геттер для копии словаря кошельков"""
        return self._wallets.copy()
    
    def add_currency(self, currency_code: str, initial_balance: float = 0.0):
        """Добавляет новый кошелёк в портфель"""
        if not isinstance(currency_code, str) or not currency_code:
            raise ValueError("Код валюты должен быть непустой строкой")
        
        if currency_code in self._wallets:
            raise ValueError(f"Кошелёк с валютой {currency_code} уже существует")
        
        self._wallets[currency_code] = Wallet(currency_code, initial_balance)
    
    def get_wallet(self, currency_code: str) -> Wallet:
        """Возвращает объект Wallet по коду валюты"""
        if currency_code not in self._wallets:
            raise ValueError(f"Кошелёк с валютой {currency_code} не найден")
        return self._wallets[currency_code]
    
    def get_total_value(self, base_currency: str = 'USD') -> float:
        """Возвращает общую стоимость всех валют в базовой валюте"""
        # Фиктивные курсы для демонстрации
        exchange_rates = {
            'USD': 1.0,
            'EUR': 1.1,    # 1 EUR = 1.1 USD
            'BTC': 50000.0, # 1 BTC = 50000 USD
            'RUB': 0.011    # 1 RUB = 0.011 USD
        }
        
        total_value = 0.0
        
        for currency_code, wallet in self._wallets.items():
            if currency_code == base_currency:
                total_value += wallet.balance
            else:
                # Конвертируем через USD как промежуточную валюту
                if currency_code in exchange_rates and base_currency in exchange_rates:
                    usd_value = wallet.balance * exchange_rates[currency_code]
                    total_value += usd_value / exchange_rates[base_currency]
        
        return total_value
    
    def buy_currency(self, from_currency: str, to_currency: str, amount: float, rate: float):
        """Покупка валюты (списание с USD, начисление в target)"""
        if from_currency not in self._wallets:
            raise ValueError(f"Кошелёк {from_currency} не найден")
        if to_currency not in self._wallets:
            raise ValueError(f"Кошелёк {to_currency} не найден")
        
        # Списываем с исходной валюты
        self._wallets[from_currency].withdraw(amount)
        
        # Начисляем в целевую валюту (amount * rate)
        self._wallets[to_currency].deposit(amount * rate)
    
    def sell_currency(self, from_currency: str, to_currency: str, amount: float, rate: float):
        """Продажа валюты (списание с source, начисление в USD)"""
        # Это обратная операция к buy_currency
        self.buy_currency(from_currency, to_currency, amount, 1/rate)
    
    def to_dict(self) -> dict:
        """Для сериализации в JSON"""
        return {
            "user_id": self._user_id,
            "wallets": {code: wallet.to_dict() for code, wallet in self._wallets.items()}
        }
    
    def __str__(self):
        return f"Portfolio(user_id={self._user_id}, wallets={len(self._wallets)})"