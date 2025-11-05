import hashlib
import secrets
from datetime import datetime
from typing import Dict, Optional, Tuple

from .models import User, Portfolio, Wallet
from .utils import load_json, save_json, get_timestamp, is_fresh

class UserService:
    @staticmethod
    def register_user(username: str, password: str) -> Tuple[bool, str]:
        """Регистрирует нового пользователя"""
        users = load_json('users.json')
        
        # Проверка уникальности username
        for user_data in users.values():
            if user_data.get('username') == username:
                return False, f"Имя пользователя '{username}' уже используется"
        
        # Проверка длины пароля
        if len(password) < 4:
            return False, "Пароль должен быть не короче 4 символов"
        
        # Генерация user_id
        user_id = str(max([int(uid) for uid in users.keys()] + [0]) + 1)
        
        # Хеширование пароля
        salt = secrets.token_hex(16)
        hashed_password = hashlib.sha256((password + salt).encode()).hexdigest()
        
        # Создание пользователя
        user_data = {
            'user_id': user_id,
            'username': username,
            'hashed_password': hashed_password,
            'salt': salt,
            'registration_date': get_timestamp()
        }
        
        users[user_id] = user_data
        save_json('users.json', users)
        
        # Создание пустого портфеля
        PortfolioService.create_portfolio(user_id)
        
        return True, f"Пользователь '{username}' зарегистрирован (id={user_id}). Войдите: login --username {username} --password ****"
    
    @staticmethod
    def login_user(username: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """Авторизует пользователя"""
        users = load_json('users.json')
        
        # Поиск пользователя
        user_data = None
        for uid, data in users.items():
            if data.get('username') == username:
                user_data = data
                break
        
        if not user_data:
            return False, f"Пользователь '{username}' не найден", None
        
        # Проверка пароля
        salt = user_data['salt']
        hashed_input = hashlib.sha256((password + salt).encode()).hexdigest()
        
        if hashed_input != user_data['hashed_password']:
            return False, "Неверный пароль", None
        
        # Создание объекта User
        user = User(
            user_id=int(user_data['user_id']),
            username=user_data['username'],
            password=password,  # передаем исходный пароль для создания объекта
            registration_date=datetime.fromisoformat(user_data['registration_date'])
        )
        
        return True, f"Вы вошли как '{username}'", user

class PortfolioService:
    @staticmethod
    def create_portfolio(user_id: str):
        """Создает пустой портфель для пользователя"""
        portfolios = load_json('portfolios.json')
        portfolios[user_id] = {'wallets': {}}
        save_json('portfolios.json', portfolios)
    
    @staticmethod
    def get_portfolio(user_id: int) -> Portfolio:
        """Загружает портфель пользователя"""
        portfolios = load_json('portfolios.json')
        user_portfolio = portfolios.get(str(user_id), {'wallets': {}})
        
        portfolio = Portfolio(user_id=user_id)
        
        for currency_code, wallet_data in user_portfolio.get('wallets', {}).items():
            portfolio.add_currency(currency_code, wallet_data.get('balance', 0.0))
        
        return portfolio
    
    @staticmethod
    def save_portfolio(portfolio: Portfolio):
        """Сохраняет портфель пользователя"""
        portfolios = load_json('portfolios.json')
        portfolios[str(portfolio.user_id)] = portfolio.to_dict()
        save_json('portfolios.json', portfolios)

class RateService:
    @staticmethod
    def get_exchange_rate(from_currency: str, to_currency: str) -> Tuple[bool, float, str]:
        """Получает курс обмена валют"""
        rates = load_json('rates.json')
        
        # Проверяем свежесть данных
        last_refresh = rates.get('last_refresh', '')
        if not is_fresh(last_refresh):
            # Обновляем курсы если данные устарели
            RateService._update_rates()
            rates = load_json('rates.json')
        
        pair_key = f"{from_currency}_{to_currency}"
        
        if pair_key in rates:
            rate_data = rates[pair_key]
            return True, rate_data['rate'], rate_data['updated_at']
        
        return False, 0.0, ""
    
    @staticmethod
    def _update_rates():
        """Обновляет курсы валют (заглушка)"""
        rates = {
            "EUR_USD": {"rate": 1.0786, "updated_at": get_timestamp()},
            "USD_EUR": {"rate": 0.927, "updated_at": get_timestamp()},
            "BTC_USD": {"rate": 59337.21, "updated_at": get_timestamp()},
            "USD_BTC": {"rate": 0.00001685, "updated_at": get_timestamp()},
            "RUB_USD": {"rate": 0.01016, "updated_at": get_timestamp()},
            "USD_RUB": {"rate": 98.42, "updated_at": get_timestamp()},
            "ETH_USD": {"rate": 3720.00, "updated_at": get_timestamp()},
            "USD_ETH": {"rate": 0.0002688, "updated_at": get_timestamp()},
            "source": "StubService",
            "last_refresh": get_timestamp()
        }
        save_json('rates.json', rates)