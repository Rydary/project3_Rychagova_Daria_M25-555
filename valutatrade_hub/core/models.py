import hashlib
import secrets
from datetime import datetime
from typing import Dict, Optional, Any
from .exceptions import InsufficientFundsError, ValidationError
from .currencies import Currency, get_currency


class User:
    """
    Класс пользователя системы с приватными атрибутами и валидацией
    """
    
    def __init__(self, user_id: int, username: str, password: str, 
                 registration_date: Optional[datetime] = None):
        self._user_id = user_id
        self._username = self._validate_username(username)
        self._salt = secrets.token_hex(16)
        self._hashed_password = self._hash_password(password, self._salt)
        self._registration_date = registration_date or datetime.now()
        self._is_active = True
    
    def _validate_username(self, username: str) -> str:
        """Валидация имени пользователя"""
        if not isinstance(username, str):
            raise ValidationError("Имя пользователя должно быть строкой")
        if not username.strip():
            raise ValidationError("Имя пользователя не может быть пустым")
        if len(username) < 3:
            raise ValidationError("Имя пользователя должно содержать минимум 3 символа")
        if len(username) > 50:
            raise ValidationError("Имя пользователя не может превышать 50 символов")
        return username.strip()
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Хеширование пароля с солью"""
        if not isinstance(password, str):
            raise ValidationError("Пароль должен быть строкой")
        if len(password) < 4:
            raise ValidationError("Пароль должен содержать минимум 4 символа")
        
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    # Геттеры
    @property
    def user_id(self) -> int:
        return self._user_id
    
    @property
    def username(self) -> str:
        return self._username
    
    @property
    def registration_date(self) -> datetime:
        return self._registration_date
    
    @property
    def is_active(self) -> bool:
        return self._is_active
    
    # Сеттеры с валидацией
    @username.setter
    def username(self, value: str):
        self._username = self._validate_username(value)
    
    def change_password(self, old_password: str, new_password: str) -> bool:
        """
        Изменяет пароль пользователя
        
        Args:
            old_password: Старый пароль для проверки
            new_password: Новый пароль
            
        Returns:
            True если пароль успешно изменен
            
        Raises:
            ValidationError: Если пароли невалидны
        """
        if not self.verify_password(old_password):
            raise ValidationError("Неверный текущий пароль")
        
        self._salt = secrets.token_hex(16)
        self._hashed_password = self._hash_password(new_password, self._salt)
        return True
    
    def verify_password(self, password: str) -> bool:
        """Проверяет введённый пароль на совпадение"""
        if not isinstance(password, str):
            return False
        
        hashed_input = self._hash_password(password, self._salt)
        return hashed_input == self._hashed_password
    
    def deactivate(self):
        """Деактивирует пользователя"""
        self._is_active = False
    
    def activate(self):
        """Активирует пользователя"""
        self._is_active = True
    
    def get_user_info(self) -> Dict[str, Any]:
        """Возвращает информацию о пользователе (без пароля)"""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.strftime("%Y-%m-%d %H:%M:%S"),
            "is_active": self._is_active
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Для сериализации в JSON"""
        return {
            'user_id': self._user_id,
            'username': self._username,
            'hashed_password': self._hashed_password,
            'salt': self._salt,
            'registration_date': self._registration_date.isoformat(),
            'is_active': self._is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Создает объект User из словаря"""
        user = cls(
            user_id=data['user_id'],
            username=data['username'],
            password="temporary",  # Пароль будет переопределен
            registration_date=datetime.fromisoformat(data['registration_date'])
        )
        user._hashed_password = data['hashed_password']
        user._salt = data['salt']
        user._is_active = data.get('is_active', True)
        return user
    
    def __str__(self) -> str:
        return f"User(id={self._user_id}, username='{self._username}')"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, User):
            return False
        return self._user_id == other._user_id


class Wallet:
    """
    Класс кошелька пользователя для одной конкретной валюты
    """
    
    def __init__(self, currency_code: str, balance: float = 0.0):
        self._currency_code = self._validate_currency_code(currency_code)
        self._balance = self._validate_balance(balance)
        self._currency_obj: Optional[Currency] = None
    
    def _validate_currency_code(self, currency_code: str) -> str:
        """Валидация кода валюты"""
        if not isinstance(currency_code, str):
            raise ValidationError("Код валюты должен быть строкой")
        
        currency_code = currency_code.upper().strip()
        if not currency_code:
            raise ValidationError("Код валюты не может быть пустым")
        
        # Проверяем что валюта поддерживается
        try:
            self._currency_obj = get_currency(currency_code)
        except Exception:
            raise ValidationError(f"Валюта '{currency_code}' не поддерживается")
        
        return currency_code
    
    def _validate_balance(self, balance: float) -> float:
        """Валидация баланса"""
        if not isinstance(balance, (int, float)):
            raise ValidationError("Баланс должен быть числом")
        if balance < 0:
            raise ValidationError("Баланс не может быть отрицательным")
        return float(balance)
    
    def _validate_amount(self, amount: float) -> float:
        """Валидация суммы операций"""
        if not isinstance(amount, (int, float)):
            raise ValidationError("Сумма должна быть числом")
        if amount <= 0:
            raise ValidationError("Сумма должна быть положительной")
        return float(amount)
    
    # Геттеры
    @property
    def currency_code(self) -> str:
        return self._currency_code
    
    @property
    def balance(self) -> float:
        return self._balance
    
    @property
    def currency_info(self) -> Optional[Currency]:
        return self._currency_obj
    
    # Сеттер баланса с валидацией
    @balance.setter
    def balance(self, value: float):
        self._balance = self._validate_balance(value)
    
    def deposit(self, amount: float):
        """
        Пополнение баланса
        
        Args:
            amount: Сумма пополнения
            
        Raises:
            ValidationError: Если сумма невалидна
        """
        validated_amount = self._validate_amount(amount)
        self._balance += validated_amount
    
    def withdraw(self, amount: float):
        """
        Снятие средств
        
        Args:
            amount: Сумма снятия
            
        Raises:
            InsufficientFundsError: Если недостаточно средств
            ValidationError: Если сумма невалидна
        """
        validated_amount = self._validate_amount(amount)
        
        if validated_amount > self._balance:
            raise InsufficientFundsError(
                available=self._balance,
                required=validated_amount,
                code=self._currency_code
            )
        
        self._balance -= validated_amount
    
    def get_balance_info(self) -> Dict[str, Any]:
        """Возвращает информацию о текущем балансе"""
        currency_info = self._currency_obj.get_display_info() if self._currency_obj else "Unknown"
        
        return {
            "currency_code": self._currency_code,
            "balance": self._balance,
            "currency_info": currency_info,
            "display_balance": f"{self._balance:.4f} {self._currency_code}"
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Для сериализации в JSON"""
        return {
            'currency_code': self._currency_code,
            'balance': self._balance
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Wallet':
        """Создает объект Wallet из словаря"""
        return cls(
            currency_code=data['currency_code'],
            balance=data['balance']
        )
    
    def __str__(self) -> str:
        return f"Wallet({self._currency_code}: {self._balance:.4f})"
    
    def __repr__(self) -> str:
        return f"Wallet(currency_code='{self._currency_code}', balance={self._balance})"


class Portfolio:
    """
    Класс для управления всеми кошельками одного пользователя
    """
    
    def __init__(self, user_id: int):
        self._user_id = user_id
        self._wallets: Dict[str, Wallet] = {}
        self._created_at = datetime.now()
        self._last_updated = datetime.now()
    
    # Геттеры
    @property
    def user_id(self) -> int:
        return self._user_id
    
    @property
    def wallets(self) -> Dict[str, Wallet]:
        return self._wallets.copy()
    
    @property
    def created_at(self) -> datetime:
        return self._created_at
    
    @property
    def last_updated(self) -> datetime:
        return self._last_updated
    
    def add_wallet(self, currency_code: str, initial_balance: float = 0.0) -> Wallet:
        """
        Добавляет новый кошелёк в портфель
        
        Args:
            currency_code: Код валюты
            initial_balance: Начальный баланс
            
        Returns:
            Созданный объект Wallet
            
        Raises:
            ValidationError: Если кошелек уже существует или валюта невалидна
        """
        currency_code = currency_code.upper()
        
        if currency_code in self._wallets:
            raise ValidationError(f"Кошелёк с валютой '{currency_code}' уже существует")
        
        wallet = Wallet(currency_code, initial_balance)
        self._wallets[currency_code] = wallet
        self._update_timestamp()
        
        return wallet
    
    def get_wallet(self, currency_code: str) -> Wallet:
        """
        Возвращает объект Wallet по коду валюты
        
        Args:
            currency_code: Код валюты
            
        Returns:
            Объект Wallet
            
        Raises:
            ValidationError: Если кошелек не найден
        """
        currency_code = currency_code.upper()
        
        if currency_code not in self._wallets:
            raise ValidationError(f"Кошелёк с валютой '{currency_code}' не найден")
        
        return self._wallets[currency_code]
    
    def has_wallet(self, currency_code: str) -> bool:
        """Проверяет наличие кошелька с указанной валютой"""
        return currency_code.upper() in self._wallets
    
    def remove_wallet(self, currency_code: str) -> bool:
        """
        Удаляет кошелек из портфеля
        
        Args:
            currency_code: Код валюты
            
        Returns:
            True если кошелек удален, False если не найден
        """
        currency_code = currency_code.upper()
        
        if currency_code in self._wallets:
            # Не позволяем удалять кошельки с ненулевым балансом
            wallet = self._wallets[currency_code]
            if wallet.balance > 0:
                raise ValidationError(
                    f"Нельзя удалить кошелёк {currency_code} с ненулевым балансом: {wallet.balance}"
                )
            
            del self._wallets[currency_code]
            self._update_timestamp()
            return True
        
        return False
    
    def get_total_balance(self, currency_code: str) -> float:
        """
        Возвращает общий баланс в указанной валюте
        
        Args:
            currency_code: Код валюты для фильтрации
            
        Returns:
            Суммарный баланс
        """
        currency_code = currency_code.upper()
        total = 0.0
        
        for wallet in self._wallets.values():
            if wallet.currency_code == currency_code:
                total += wallet.balance
        
        return total
    
    def get_portfolio_info(self) -> Dict[str, Any]:
        """Возвращает полную информацию о портфеле"""
        wallet_info = {}
        total_wallets = len(self._wallets)
        
        for currency_code, wallet in self._wallets.items():
            wallet_info[currency_code] = wallet.get_balance_info()
        
        return {
            "user_id": self._user_id,
            "total_wallets": total_wallets,
            "wallets": wallet_info,
            "created_at": self._created_at.isoformat(),
            "last_updated": self._last_updated.isoformat()
        }
    
    def _update_timestamp(self):
        """Обновляет временную метку последнего изменения"""
        self._last_updated = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Для сериализации в JSON"""
        return {
            'user_id': self._user_id,
            'wallets': {code: wallet.to_dict() for code, wallet in self._wallets.items()},
            'created_at': self._created_at.isoformat(),
            'last_updated': self._last_updated.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Portfolio':
        """Создает объект Portfolio из словаря"""
        portfolio = cls(user_id=data['user_id'])
        
        # Восстанавливаем временные метки если они есть
        if 'created_at' in data:
            portfolio._created_at = datetime.fromisoformat(data['created_at'])
        if 'last_updated' in data:
            portfolio._last_updated = datetime.fromisoformat(data['last_updated'])
        
        # Восстанавливаем кошельки
        for currency_code, wallet_data in data.get('wallets', {}).items():
            portfolio._wallets[currency_code] = Wallet.from_dict(wallet_data)
        
        return portfolio
    
    def __str__(self) -> str:
        return f"Portfolio(user_id={self._user_id}, wallets={len(self._wallets)})"
    
    def __repr__(self) -> str:
        return f"Portfolio(user_id={self._user_id}, wallets={list(self._wallets.keys())})"
    
    def __contains__(self, currency_code: str) -> bool:
        return currency_code.upper() in self._wallets
    
    def __len__(self) -> int:
        return len(self._wallets)