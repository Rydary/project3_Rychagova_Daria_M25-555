import argparse
import sys
from typing import Optional

from ..core.usecases import UserService, PortfolioService, RateService
from ..core.models import User

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
        if not currency or not isinstance(currency, str) or not currency.isalpha():
            return False
        return True
    
    def _validate_amount(self, amount: float) -> bool:
        """Валидирует сумму"""
        return isinstance(amount, (int, float)) and amount > 0
    
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
        
        if not self._validate_currency(args.currency):
            print(f"Некорректный код валюты: '{args.currency}'")
            return False
        
        if not self._validate_amount(args.amount):
            print("'amount' должен быть положительным числом")
            return False
        
        # Получаем курс
        success, rate, updated_at = RateService.get_exchange_rate(args.currency, 'USD')
        if not success:
            print(f"Не удалось получить курс для {args.currency}→USD")
            return False
        
        # Загружаем и обновляем портфель
        portfolio = PortfolioService.get_portfolio(self.current_user.user_id)
        
        # Добавляем кошелек если его нет
        if args.currency not in portfolio.wallets:
            portfolio.add_currency(args.currency, 0.0)
        
        wallet = portfolio.get_wallet(args.currency)
        old_balance = wallet.balance
        wallet.deposit(args.amount)
        
        # Сохраняем изменения
        PortfolioService.save_portfolio(portfolio)
        
        cost_usd = args.amount * rate
        
        print(f"Покупка выполнена: {args.amount:.4f} {args.currency} по курсу {rate:.2f} USD/{args.currency}")
        print("Изменения в портфеле:")
        print(f"  - {args.currency}: было {old_balance:.4f} → стало {wallet.balance:.4f}")
        print(f"Оценочная стоимость покупки: {cost_usd:,.2f} USD")
        
        return True
    
    def sell(self, args):
        """Команда sell"""
        if not self._check_auth():
            return False
        
        if not self._validate_currency(args.currency):
            print(f"Некорректный код валюты: '{args.currency}'")
            return False
        
        if not self._validate_amount(args.amount):
            print("'amount' должен быть положительным числом")
            return False
        
        # Загружаем портфель
        portfolio = PortfolioService.get_portfolio(self.current_user.user_id)
        
        # Проверяем наличие кошелька
        if args.currency not in portfolio.wallets:
            print(f"У вас нет кошелька '{args.currency}'. Добавьте валюту: она создаётся автоматически при первой покупке.")
            return False
        
        wallet = portfolio.get_wallet(args.currency)
        
        # Проверяем достаточно ли средств
        if args.amount > wallet.balance:
            print(f"Недостаточно средств: доступно {wallet.balance:.4f} {args.currency}, требуется {args.amount:.4f} {args.currency}")
            return False
        
        # Получаем курс
        success, rate, updated_at = RateService.get_exchange_rate(args.currency, 'USD')
        if not success:
            print(f"Не удалось получить курс для {args.currency}→USD")
            return False
        
        old_balance = wallet.balance
        wallet.withdraw(args.amount)
        
        # Сохраняем изменения
        PortfolioService.save_portfolio(portfolio)
        
        revenue_usd = args.amount * rate
        
        print(f"Продажа выполнена: {args.amount:.4f} {args.currency} по курсу {rate:.2f} USD/{args.currency}")
        print("Изменения в портфеле:")
        print(f"  - {args.currency}: было {old_balance:.4f} → стало {wallet.balance:.4f}")
        print(f"Оценочная выручка: {revenue_usd:,.2f} USD")
        
        return True
    
    def get_rate(self, args):
        """Команда get-rate"""
        if not self._validate_currency(args.from_currency) or not self._validate_currency(args.to_currency):
            print("Некорректные коды валют")
            return False
        
        success, rate, updated_at = RateService.get_exchange_rate(args.from_currency, args.to_currency)
        
        if not success:
            print(f"Курс {args.from_currency}→{args.to_currency} недоступен. Повторите попытку позже.")
            return False
        
        # Получаем обратный курс
        _, reverse_rate, _ = RateService.get_exchange_rate(args.to_currency, args.from_currency)
        
        updated_time = updated_at.split('T')[1].split('.')[0] if 'T' in updated_at else updated_at
        
        print(f"Курс {args.from_currency}→{args.to_currency}: {rate:.8f} (обновлено: {updated_time})")
        print(f"Обратный курс {args.to_currency}→{args.from_currency}: {reverse_rate:.2f}")
        
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
    
    args = parser.parse_args()
    
    # Выполняем команду
    command_map = {
        'register': cli.register,
        'login': cli.login,
        'show-portfolio': cli.show_portfolio,
        'buy': cli.buy,
        'sell': cli.sell,
        'get-rate': cli.get_rate
    }
    
    try:
        success = command_map[args.command](args)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()