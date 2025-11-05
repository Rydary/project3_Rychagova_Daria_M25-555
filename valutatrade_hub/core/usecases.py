# core/usecases.py
import hashlib
import secrets
from datetime import datetime
from typing import Dict, Optional, Tuple, Any
from .exceptions import InsufficientFundsError, CurrencyNotFoundError, ApiRequestError, ValidationError
from .models import User, Portfolio, Wallet
from .currencies import get_currency, get_supported_currencies
from .utils import validate_currency_code, validate_amount
from ..infra.database import db
from ..infra.settings import settings
from ..decorators import log_action


class UserService:
    
    @staticmethod
    @log_action(verbose=True)
    def register_user(username: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """Регистрирует нового пользователя"""
        try:
            # Загрузка существующих пользователей
            users_data = db.load_collection('users')
            
            # Проверка уникальности username
            for user_data in users_data.values():
                if user_data.get('username') == username:
                    return False, f"Имя пользователя '{username}' уже занято", None
            
            # Генерация user_id
            user_ids = [int(uid) for uid in users_data.keys() if uid.isdigit()]
            user_id = max(user_ids) + 1 if user_ids else 1
            
            # Создание пользователя
            user = User(user_id=user_id, username=username, password=password)
            
            # Сохранение пользователя
            users_data[str(user_id)] = user.to_dict()
            db.save_collection('users', users_data)
            
            # Создание пустого портфеля
            PortfolioService.create_portfolio(user_id)
            
            return True, f"Пользователь '{username}' зарегистрирован (id={user_id}). Войдите: login --username {username} --password ****", user
            
        except ValidationError as e:
            return False, str(e), None
        except Exception as e:
            return False, f"Ошибка при регистрации: {e}", None
    
    @staticmethod
    @log_action(verbose=True)
    def login_user(username: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """Авторизует пользователя"""
        try:
            users_data = db.load_collection('users')
            
            # Поиск пользователя
            user_data = None
            for uid, data in users_data.items():
                if data.get('username') == username:
                    user_data = data
                    break
            
            if not user_data:
                return False, f"Пользователь '{username}' не найден", None
            
            # Проверка активности пользователя
            if not user_data.get('is_active', True):
                return False, "Учетная запись деактивирована", None
            
            # Создание объекта User и проверка пароля
            user = User.from_dict(user_data)
            
            if not user.verify_password(password):
                return False, "Неверный пароль", None
            
            return True, f"Вы вошли как '{username}'", user
            
        except Exception as e:
            return False, f"Ошибка при входе: {e}", None


class PortfolioService:
    
    @staticmethod
    def create_portfolio(user_id: int):
        """Создает пустой портфель для пользователя"""
        portfolios_data = db.load_collection('portfolios')
        portfolio = Portfolio(user_id=user_id)
        portfolios_data[str(user_id)] = portfolio.to_dict()
        db.save_collection('portfolios', portfolios_data)
    
    @staticmethod
    def get_portfolio(user_id: int) -> Portfolio:
        """Загружает портфель пользователя"""
        portfolios_data = db.load_collection('portfolios')
        portfolio_data = portfolios_data.get(str(user_id), {})
        
        if portfolio_data:
            return Portfolio.from_dict(portfolio_data)
        else:
            # Создаем новый портфель если не найден
            portfolio = Portfolio(user_id=user_id)
            return portfolio
    
    @staticmethod
    def save_portfolio(portfolio: Portfolio):
        """Сохраняет портфель пользователя"""
        portfolios_data = db.load_collection('portfolios')
        portfolios_data[str(portfolio.user_id)] = portfolio.to_dict()
        db.save_collection('portfolios', portfolios_data)
    
    @staticmethod
    @log_action(verbose=True)
    def buy_currency(user_id: int, currency_code: str, amount: float) -> Tuple[bool, str, Dict[str, Any]]:
        """Покупка валюты"""
        try:
            # Валидация входа
            currency_code = validate_currency_code(currency_code)
            amount = validate_amount(amount)
            
            # Получение информации о валюте
            currency = get_currency(currency_code)
            
            # Загрузка портфеля
            portfolio = PortfolioService.get_portfolio(user_id)
            
            # Создание кошелька если не существует
            if not portfolio.has_wallet(currency_code):
                portfolio.add_wallet(currency_code, 0.0)
            
            wallet = portfolio.get_wallet(currency_code)
            old_balance = wallet.balance
            
            # Пополнение баланса
            wallet.deposit(amount)
            
            # Получение курса для расчета стоимости
            success, rate, updated_at = RateService.get_exchange_rate(currency_code, 'USD')
            cost_usd = amount * rate if success else 0.0
            
            # Сохранение изменений
            PortfolioService.save_portfolio(portfolio)
            
            result_info = {
                'currency_code': currency_code,
                'amount': amount,
                'old_balance': old_balance,
                'new_balance': wallet.balance,
                'rate': rate if success else None,
                'cost_usd': cost_usd,
                'currency_info': currency.get_display_info()
            }
            
            return True, f"Покупка выполнена: {amount:.4f} {currency_code}", result_info
            
        except CurrencyNotFoundError as e:
            return False, str(e), {}
        except ValidationError as e:
            return False, str(e), {}
        except Exception as e:
            return False, f"Ошибка при покупке: {e}", {}
    
    @staticmethod
    @log_action(verbose=True)
    def sell_currency(user_id: int, currency_code: str, amount: float) -> Tuple[bool, str, Dict[str, Any]]:
        """Продажа валюты"""
        try:
            # Валидация входа
            currency_code = validate_currency_code(currency_code)
            amount = validate_amount(amount)
            
            # Получение информации о валюте
            currency = get_currency(currency_code)
            
            # Загрузка портфеля
            portfolio = PortfolioService.get_portfolio(user_id)
            
            # Проверка наличия кошелька
            if not portfolio.has_wallet(currency_code):
                return False, f"У вас нет кошелька '{currency_code}'. Добавьте валюту: она создаётся автоматически при первой покупке.", {}
            
            wallet = portfolio.get_wallet(currency_code)
            old_balance = wallet.balance
            
            # Снятие средств
            wallet.withdraw(amount)
            
            # Получение курса для расчета выручки
            success, rate, updated_at = RateService.get_exchange_rate(currency_code, 'USD')
            revenue_usd = amount * rate if success else 0.0
            
            # Сохранение изменений
            PortfolioService.save_portfolio(portfolio)
            
            result_info = {
                'currency_code': currency_code,
                'amount': amount,
                'old_balance': old_balance,
                'new_balance': wallet.balance,
                'rate': rate if success else None,
                'revenue_usd': revenue_usd,
                'currency_info': currency.get_display_info()
            }
            
            return True, f"Продажа выполнена: {amount:.4f} {currency_code}", result_info
            
        except InsufficientFundsError as e:
            return False, str(e), {}
        except CurrencyNotFoundError as e:
            return False, str(e), {}
        except ValidationError as e:
            return False, str(e), {}
        except Exception as e:
            return False, f"Ошибка при продаже: {e}", {}


class RateService:
    
    @staticmethod
    def get_exchange_rate(from_currency: str, to_currency: str) -> Tuple[bool, float, str]:
        """Получает курс обмена валют"""
        try:
            # Валидация кодов валют
            from_currency = validate_currency_code(from_currency)
            to_currency = validate_currency_code(to_currency)
            
            # Получение информации о валютах
            get_currency(from_currency)
            get_currency(to_currency)
            
            # Загрузка кеша курсов
            rates_data = db.load_collection('rates')
            
            # Проверка свежести данных
            last_refresh = rates_data.get('last_refresh', '')
            if not RateService._is_fresh_data(last_refresh):
                RateService._update_rates_cache()
                rates_data = db.load_collection('rates')
            
            pair_key = f"{from_currency}_{to_currency}"
            
            if pair_key in rates_data:
                rate_data = rates_data[pair_key]
                return True, rate_data['rate'], rate_data['updated_at']
            
            # Если прямой курс не найден, пытаемся вычислить через USD
            if from_currency != 'USD' and to_currency != 'USD':
                usd_from_success, usd_from_rate, _ = RateService.get_exchange_rate(from_currency, 'USD')
                usd_to_success, usd_to_rate, _ = RateService.get_exchange_rate('USD', to_currency)
                
                if usd_from_success and usd_to_success:
                    calculated_rate = usd_from_rate * usd_to_rate
                    return True, calculated_rate, datetime.now().isoformat()
            
            raise ApiRequestError(f"Курс {from_currency}→{to_currency} недоступен")
            
        except CurrencyNotFoundError as e:
            return False, 0.0, str(e)
        except ApiRequestError as e:
            return False, 0.0, str(e)
        except Exception as e:
            return False, 0.0, f"Ошибка при получении курса: {e}"
    
    @staticmethod
    def _is_fresh_data(timestamp: str) -> bool:
        """Проверяет свежесть данных"""
        if not timestamp:
            return False
        
        try:
            data_time = datetime.fromisoformat(timestamp)
            ttl_seconds = settings.get('rates_ttl_seconds', 300)
            return (datetime.now() - data_time).total_seconds() < ttl_seconds
        except ValueError:
            return False
    
    @staticmethod
    def _update_rates_cache():
        """Обновляет кеш курсов валют"""
        try:
            # Здесь будет интеграция с Parser Service
            # Пока используем заглушку с фиксированными курсами
            
            rates_data = {
                "EUR_USD": {"rate": 1.0786, "updated_at": datetime.now().isoformat()},
                "USD_EUR": {"rate": 0.927, "updated_at": datetime.now().isoformat()},
                "BTC_USD": {"rate": 59337.21, "updated_at": datetime.now().isoformat()},
                "USD_BTC": {"rate": 0.00001685, "updated_at": datetime.now().isoformat()},
                "RUB_USD": {"rate": 0.01016, "updated_at": datetime.now().isoformat()},
                "USD_RUB": {"rate": 98.42, "updated_at": datetime.now().isoformat()},
                "ETH_USD": {"rate": 3720.00, "updated_at": datetime.now().isoformat()},
                "USD_ETH": {"rate": 0.0002688, "updated_at": datetime.now().isoformat()},
                "source": "StubService",
                "last_refresh": datetime.now().isoformat()
            }
            
            db.save_collection('rates', rates_data)
            
        except Exception as e:
            raise ApiRequestError(f"Не удалось обновить курсы: {e}")
    
    @staticmethod
    def get_supported_currency_pairs() -> Dict[str, Any]:
        """Возвращает информацию о поддерживаемых валютных парах"""
        supported_currencies = get_supported_currencies()
        pairs_info = {}
        
        for from_curr in supported_currencies.keys():
            for to_curr in supported_currencies.keys():
                if from_curr != to_curr:
                    pair_key = f"{from_curr}_{to_curr}"
                    success, rate, updated_at = RateService.get_exchange_rate(from_curr, to_curr)
                    
                    if success:
                        pairs_info[pair_key] = {
                            'rate': rate,
                            'updated_at': updated_at,
                            'from_currency': from_curr,
                            'to_currency': to_curr
                        }
        
        return pairs_info