import argparse
import sys
from typing import Optional

from ..core.usecases import UserService, PortfolioService, RateService
from ..core.models import User
from ..core.exceptions import (ValutaTradeError, InsufficientFundsError, 
                              CurrencyNotFoundError, ApiRequestError, ValidationError)
from ..core.currencies import get_supported_currencies

class CLI:
    def __init__(self):
        self.current_user: Optional[User] = None
    
    def _check_auth(self) -> bool:
        """Проверяет, авторизован ли пользователь"""
        if not self.current_user:
            print("Сначала выполните login")
            return False
        return True
    
    def _validate_currency(self, currency: str) -> bool:
        """Валидирует код валюты"""
        try:
            from ..core.utils import validate_currency_code
            validate_currency_code(currency)
            return True
        except ValidationError:
            return False

    def _validate_amount(self, amount: float) -> bool:
        """Валидирует сумму"""
        try:
            from ..core.utils import validate_amount
            validate_amount(amount)
            return True
        except ValidationError:
            return False
    
    def register(self, args):
        """Команда register"""
        success, message = UserService.register_user(args.username, args.password)
        print(message)
        return success
    
    def login(self, args):
        """Команда login"""
        success, message, user = UserService.login_user(args.username, args.password)
        if success:
            self.current_user = user
        print(message)
        return success
    
    def show_portfolio(self, args):
        """Команда show-portfolio"""
        if not self._check_auth():
            return False
        
        base_currency = args.base or 'USD'
        
        if not self._validate_currency(base_currency):
            print(f"Неизвестная базовая валюта '{base_currency}'")
            return False
        
        portfolio = PortfolioService.get_portfolio(self.current_user.user_id)
        
        if not portfolio.wallets:
            print("У вас пока нет кошельков. Используйте команду buy для покупки валюты.")
            return True
        
        print(f"Портфель пользователя '{self.current_user.username}' (база: {base_currency}):")
        
        total_value = 0.0
        for currency_code, wallet in portfolio.wallets.items():
            # Получаем курс для конвертации
            success, rate, _ = RateService.get_exchange_rate(currency_code, base_currency)
            if success:
                value_in_base = wallet.balance * rate
                total_value += value_in_base
                print(f"  - {currency_code}: {wallet.balance:.4f} → {value_in_base:.2f} {base_currency}")
            else:
                print(f"  - {currency_code}: {wallet.balance:.4f} → курс недоступен")
        
        print("-" * 40)
        print(f"ИТОГО: {total_value:,.2f} {base_currency}")
        return True
    
    def buy(self, args):
        """Команда buy"""
        if not self._check_auth():
            return False
        
        try:
            # Используем обновленный сервис
            success, message, result_info = PortfolioService.buy_currency(
                self.current_user.user_id, args.currency, args.amount
            )
            
            if success:
                print(message)
                print("Изменения в портфеле:")
                print(f"  - {args.currency}: было {result_info['old_balance']:.4f} → стало {result_info['new_balance']:.4f}")
                
                if result_info.get('rate'):
                    print(f"Оценочная стоимость покупки: {result_info['cost_usd']:,.2f} USD")
            else:
                print(f"Ошибка: {message}")
                
            return success
            
        except CurrencyNotFoundError as e:
            print(f"Ошибка: {e}")
            print("Используйте команду list-currencies для просмотра доступных валют")
            return False
        except ValidationError as e:
            print(f"Ошибка валидации: {e}")
            return False
        except Exception as e:
            print(f"Неожиданная ошибка: {e}")
            return False
    
    def sell(self, args):
        """Команда sell"""
        if not self._check_auth():
            return False
        
        try:
            success, message, result_info = PortfolioService.sell_currency(
                self.current_user.user_id, args.currency, args.amount
            )
            
            if success:
                print(message)
                print("Изменения в портфеле:")
                print(f"  - {args.currency}: было {result_info['old_balance']:.4f} → стало {result_info['new_balance']:.4f}")
                
                if result_info.get('rate'):
                    print(f"Оценочная выручка: {result_info['revenue_usd']:,.2f} USD")
            else:
                print(f"Ошибка: {message}")
                
            return success
            
        except InsufficientFundsError as e:
            print(f"Ошибка: {e}")
            return False
        except CurrencyNotFoundError as e:
            print(f"Ошибка: {e}")
            return False
        except ValidationError as e:
            print(f"Ошибка валидации: {e}")
            return False
        except Exception as e:
            print(f"Неожиданная ошибка: {e}")
            return False
    
    def get_rate(self, args):
        """Команда get-rate"""
        try:
            success, rate, error_message = RateService.get_exchange_rate(args.from_currency, args.to_currency)
            
            if success:
                # Получаем обратный курс
                _, reverse_rate, _ = RateService.get_exchange_rate(args.to_currency, args.from_currency)
                
                print(f"Курс {args.from_currency}→{args.to_currency}: {rate:.8f}")
                print(f"Обратный курс {args.to_currency}→{args.from_currency}: {reverse_rate:.8f}")
                return True
            else:
                print(f"Ошибка: {error_message}")
                
                # Специальная обработка для неизвестной валюты
                if "Неизвестная валюта" in error_message:
                    print("Используйте команду list-currencies для просмотра доступных валют")
                
                return False
                
        except CurrencyNotFoundError as e:
            print(f"Ошибка: {e}")
            print("Используйте команду list-currencies для просмотра доступных валют")
            return False
        except ApiRequestError as e:
            print(f"Ошибка: {e}")
            print("Повторите попытку позже")
            return False
        except Exception as e:
            print(f"Неожиданная ошибка: {e}")
            return False
        
    def list_currencies(self, args):
        """Команда для отображения списка поддерживаемых валют"""
        currencies = get_supported_currencies()
        
        if not currencies:
            print("Нет доступных валют")
            return True
        
        print("Поддерживаемые валюты:")
        for currency_code, currency_obj in currencies.items():
            print(f"  - {currency_obj.get_display_info()}")
        
        return True


def main():
    cli = CLI()
    parser = argparse.ArgumentParser(description='ValutaTrade Hub - Торговая платформа')
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # register command
    register_parser = subparsers.add_parser('register', help='Регистрация нового пользователя')
    register_parser.add_argument('--username', required=True, help='Имя пользователя')
    register_parser.add_argument('--password', required=True, help='Пароль')
    
    # login command
    login_parser = subparsers.add_parser('login', help='Вход в систему')
    login_parser.add_argument('--username', required=True, help='Имя пользователя')
    login_parser.add_argument('--password', required=True, help='Пароль')
    
    # show-portfolio command
    portfolio_parser = subparsers.add_parser('show-portfolio', help='Показать портфель')
    portfolio_parser.add_argument('--base', help='Базовая валюта (по умолчанию USD)')
    
    # buy command
    buy_parser = subparsers.add_parser('buy', help='Купить валюту')
    buy_parser.add_argument('--currency', required=True, help='Код покупаемой валюты')
    buy_parser.add_argument('--amount', type=float, required=True, help='Количество')
    
    # sell command
    sell_parser = subparsers.add_parser('sell', help='Продать валюту')
    sell_parser.add_argument('--currency', required=True, help='Код продаваемой валюты')
    sell_parser.add_argument('--amount', type=float, required=True, help='Количество')
    
    # get-rate command
    rate_parser = subparsers.add_parser('get-rate', help='Получить курс валют')
    rate_parser.add_argument('--from', dest='from_currency', required=True, help='Исходная валюта')
    rate_parser.add_argument('--to', dest='to_currency', required=True, help='Целевая валюта')
    
    list_parser = subparsers.add_parser('list-currencies', help='Показать поддерживаемые валюты')
    
    args = parser.parse_args()
    
    # Выполняем команду
    command_map = {
        'register': cli.register,
        'login': cli.login,
        'show-portfolio': cli.show_portfolio,
        'buy': cli.buy,
        'sell': cli.sell,
        'get-rate': cli.get_rate,
        'list-currencies': cli.list_currencies
    }
    
    try:
        success = command_map[args.command](args)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()