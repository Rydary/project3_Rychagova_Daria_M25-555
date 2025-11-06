import argparse
import sys
import json
import os
from typing import Optional

from ..core.usecases import UserService, PortfolioService, RateService
from ..core.models import User
from ..core.exceptions import (ValutaTradeError, InsufficientFundsError, 
                              CurrencyNotFoundError, ApiRequestError, ValidationError)
from ..core.currencies import get_supported_currencies
from ..parser_service import RatesUpdater, RatesScheduler, RatesStorage  

class CLI:
    def __init__(self):
        self.current_user: Optional[User] = None
    
    def _check_auth(self) -> bool:
        """Проверяет, авторизован ли пользователь"""
        if not self.current_user:
            print("Сначала выполните login")
            return False
        return True
    
    def login(self, args):
        """Команда login"""
        success, message, user = UserService.login_user(args.username, args.password)
        if success:
            self.current_user = user
        print(message)
        return success
    
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
        result = UserService.register_user(args.username, args.password)
        if result[0]:
            print(f"Пользователь зарегистрирован: {result[1]}")  
        else:
            print(f"Ошибка: {result[1]}")  
    
        return result[0]
    
    
    def logout(self, args):
        """Команда logout"""
        if self.current_user:
            print(f"Вы вышли из системы ({self.current_user.username})")
            self.current_user = None 
        else:
            print("Вы не авторизованы")
        return True
    
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
                _, reverse_rate, _ = RateService.get_exchange_rate(args.to_currency, args.from_currency)
                
                print(f"Курс {args.from_currency}→{args.to_currency}: {rate:.8f}")
                print(f"Обратный курс {args.to_currency}→{args.from_currency}: {reverse_rate:.8f}")
                return True
            else:
                print(f"Ошибка: {error_message}")
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
    
    def update_rates(self, args):
        """Команда update-rates - обновление курсов валют"""
        print("Обновление курсов валют...")
        
        updater = RatesUpdater()
        sources = None
        if args.source:
            sources = [args.source.lower()]
            print(f"Обновление только из источника: {args.source}")
        
        try:
            results = updater.run_update(sources)

            if results['successful_sources']:
                print(f"Успешно обновлено из: {', '.join(results['successful_sources'])}")
                print(f"Всего курсов: {results['total_rates']}")
                print(f"Время обновления: {results['last_refresh']}")
            else:
                print("Не удалось обновить ни один источник")
            
            if results['failed_sources']:
                print("⚠️  Ошибки в источниках:")
                for failure in results['failed_sources']:
                    print(f"   - {failure['source']}: {failure['error']}")
            
            return len(results['successful_sources']) > 0
            
        except Exception as e:
            print(f"Критическая ошибка при обновлении: {str(e)}")
            return False

    def show_rates(self, args):
        """Команда show-rates - просмотр курсов из кэша"""
        storage = RatesStorage()
        cache_data = storage.load_rates_cache()
        
        if not cache_data or 'pairs' not in cache_data:
            print("Локальный кеш курсов пуст. Выполните 'update-rates', чтобы загрузить данные.")
            return False
        
        pairs = cache_data['pairs']
        last_refresh = cache_data.get('last_refresh', 'Неизвестно')
        
        print(f"Курсы из кэша (обновлено: {last_refresh})")
        print("-" * 60)
  
        filtered_pairs = {}
        if args.currency:
            currency = args.currency.upper()
            for pair, data in pairs.items():
                if currency in pair:
                    filtered_pairs[pair] = data
            
            if not filtered_pairs:
                print(f"Курс для '{args.currency}' не найден в кеше.")
                print("   Доступные валюты:")
                all_currencies = set()
                for pair in pairs.keys():
                    all_currencies.update(pair.split('_'))
                print(f"   {', '.join(sorted(all_currencies))}")
                return False
        else:
            filtered_pairs = pairs
        
        sorted_pairs = sorted(
            filtered_pairs.items(),
            key=lambda x: x[1]['rate'],
            reverse=True
        )
      
        if args.top:
            sorted_pairs = sorted_pairs[:args.top]
            print(f"Топ-{args.top} самых дорогих валют:")
        
        for pair, data in sorted_pairs:
            rate = data['rate']
            source = data.get('source', 'Unknown')
            updated = data.get('updated_at', 'Unknown')
            
            if rate >= 1000:
                rate_str = f"{rate:,.2f}"
            elif rate >= 1:
                rate_str = f"{rate:.4f}"
            else:
                rate_str = f"{rate:.8f}"
            
            print(f"  {pair}: {rate_str} ({source})")
        
        if storage.is_cache_stale():
            print("\n⚠️  Внимание: данные могут быть устаревшими.")
            print("   Выполните 'update-rates' для обновления.")
        
        return True

    def start_scheduler(self, args):
        """Команда start-scheduler - запуск фонового обновления"""
        print("🚀 Запуск планировщика обновления курсов...")
        
        scheduler = RatesScheduler()
        success = scheduler.start_scheduler()
        
        if success:
            print("Планировщик запущен")
            print(f"Интервал обновления: каждые {args.interval} минут")
        else:
            print("Не удалось запустить планировщик")
        
        return success

    def stop_scheduler(self, args):
        """Команда stop-scheduler - остановка планировщика"""
        print("Остановка планировщика...")
        
        scheduler = RatesScheduler()
        success = scheduler.stop_scheduler()
        
        if success:
            print("Планировщик остановлен")
        else:
            print("Не удалось остановить планировщик")
        
        return success
    
    def interactive(self, args=None):
        """Интерактивный режим - все команды в одной сессии"""
        print("ValutaTrade Hub - Интерактивный режим")
        print("=" * 50)
        
        while True:
            try:
                if not self.current_user:
                    print("Вы не авторизованы")
                    print("1. Войти (login)")
                    print("2. Зарегистрироваться (register)")
                    print("3. Выйти (exit)")
                    
                    choice = input("Выберите действие (1-3): ").strip()
                    
                    if choice == "1":
                        username = input("Username: ")
                        password = input("Password: ")
                        success, message, user = UserService.login_user(username, password)
                        if success:
                            self.current_user = user
                        print(f"{message}")
                        
                    elif choice == "2":
                        username = input("Username: ")
                        password = input("Password: ")
                        success, message, user = UserService.register_user(username, password)
                        print(f"{message}")
                        
                    elif choice == "3":
                        print("До свидания!")
                        break
                    else:
                        print("Неверный выбор")
                        
                else:
                    print(f"Добро пожаловать, {self.current_user.username}!")
                    print("1. Показать портфель (show-portfolio)")
                    print("2. Купить валюту (buy)")
                    print("3. Продать валюту (sell)")
                    print("4. Показать курсы (show-rates)")
                    print("5. Обновить курсы (update-rates)")
                    print("6. Выйти (logout)")
                    
                    choice = input("\nВыберите действие (1-6): ").strip()
                    
                    if choice == "1":
                        base = input("Базовая валюта (по умолчанию USD): ").strip() or "USD"
                        class PortfolioArgs:
                            pass
                        args = PortfolioArgs()
                        args.base = base  
                        self.show_portfolio(args)
                        
                    elif choice == "2":
                        currency = input("Валюта для покупки (например EUR): ").strip().upper()
                        amount = float(input("Количество: ").strip())
                        class BuyArgs:
                            def __init__(self):
                                self.currency = currency
                                self.amount = amount
                                
                        self.buy(BuyArgs())
                        
                    elif choice == "3":
                        currency = input("Валюта для продажи (например EUR): ").strip()
                        amount = float(input("Количество: ").strip())
                        class SellArgs:
                            def __init__(self):
                                self.currency = currency
                                self.amount = amount
                                
                        self.sell(SellArgs())
                        
                    elif choice == "4":
                        class ShowRatesArgs:
                            def __init__(self):
                                self.currency = None  
                                self.top = None      
                                self.base = "USD"    
                        
                        self.show_rates(ShowRatesArgs())
                        
                    elif choice == "5":
                        class UpdateRatesArgs:
                            def __init__(self):
                                self.source = None  
                                
                        self.update_rates(UpdateRatesArgs())
                        
                    elif choice == "6":
                        self.current_user = None
                        print("Вы вышли из системы")
                        
                    else:
                        print("Неверный выбор")
                        
            except KeyboardInterrupt:
                print("Выход...")
                break
            except Exception as e:
                print(f"Ошибка: {e}")


def main():
    cli = CLI()
    
    if len(sys.argv) == 1:
        cli.interactive()
        return
    
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
    
    # logout command
    logout_parser = subparsers.add_parser('logout', help='Выход из системы')
    
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
    
    # list-currencies command
    list_parser = subparsers.add_parser('list-currencies', help='Показать поддерживаемые валюты')
    
    # update-rates command
    update_parser = subparsers.add_parser('update-rates', help='Обновить курсы валют')
    update_parser.add_argument('--source', choices=['coingecko', 'exchangerate'], 
                              help='Обновить только из указанного источника')

    # show-rates command
    show_rates_parser = subparsers.add_parser('show-rates', help='Показать курсы из кэша')
    show_rates_parser.add_argument('--currency', help='Показать курс только для указанной валюты')
    show_rates_parser.add_argument('--top', type=int, help='Показать N самых дорогих криптовалют')
    show_rates_parser.add_argument('--base', help='Базовая валюта (в разработке)')

    # start-scheduler command
    scheduler_start_parser = subparsers.add_parser('start-scheduler', help='Запустить фоновое обновление курсов')
    scheduler_start_parser.add_argument('--interval', type=int, default=30, help='Интервал обновления в минутах')

    # stop-scheduler command  
    scheduler_stop_parser = subparsers.add_parser('stop-scheduler', help='Остановить фоновое обновление курсов')
    
    args = parser.parse_args()
    
    command_map = {
        'register': cli.register,
        'login': cli.login,
        'logout': cli.logout,
        'show-portfolio': cli.show_portfolio,
        'buy': cli.buy,
        'sell': cli.sell,
        'get-rate': cli.get_rate,
        'list-currencies': cli.list_currencies,
        'update-rates': cli.update_rates,
        'show-rates': cli.show_rates,
        'start-scheduler': cli.start_scheduler,
        'stop-scheduler': cli.stop_scheduler,
        'interactive': cli.interactive,
    }
    
    try:
        success = command_map[args.command](args)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()