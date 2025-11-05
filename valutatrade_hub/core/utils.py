import json
import os
from datetime import datetime
from typing import Any, Dict
from .exceptions import ValidationError

DATA_DIR = "data"

def ensure_data_dir():
    """Создает папку data если её нет"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def load_json(filename: str) -> Dict[str, Any]:
    """Загружает данные из JSON файла"""
    ensure_data_dir()
    filepath = os.path.join(DATA_DIR, filename)
    
    if not os.path.exists(filepath):
        return {}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_json(filename: str, data: Dict[str, Any]):
    """Сохраняет данные в JSON файл"""
    ensure_data_dir()
    filepath = os.path.join(DATA_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

def get_timestamp() -> str:
    """Возвращает текущую timestamp в ISO формате"""
    return datetime.now().isoformat()

def is_fresh(timestamp: str, max_age_minutes: int = 5) -> bool:
    """Проверяет, свежи ли данные"""
    if not timestamp:
        return False
    
    try:
        data_time = datetime.fromisoformat(timestamp)
        return (datetime.now() - data_time).total_seconds() < max_age_minutes * 60
    except ValueError:
        return False

def validate_currency_code(currency_code: str) -> str:
    """Валидация кода валюты"""
    if not isinstance(currency_code, str):
        raise ValidationError("Код валюты должен быть строкой")
    
    currency_code = currency_code.upper().strip()
    
    if not currency_code:
        raise ValidationError("Код валюты не может быть пустым")
    
    if not 2 <= len(currency_code) <= 5:
        raise ValidationError("Код валюты должен содержать от 2 до 5 символов")
    
    if not currency_code.isalpha():
        raise ValidationError("Код валюты должен содержать только буквы")
    
    return currency_code

def validate_amount(amount: Any) -> float:
    """Валидация суммы"""
    if not isinstance(amount, (int, float)):
        raise ValidationError("Сумма должна быть числом")
    
    try:
        amount_float = float(amount)
    except (ValueError, TypeError):
        raise ValidationError("Сумма должна быть числом")
    
    if amount_float <= 0:
        raise ValidationError("Сумма должна быть положительной")
    
    return amount_float

def format_currency_amount(amount: float, currency_code: str) -> str:
    """Форматирует сумму валюты для отображения"""
    if currency_code in ['BTC', 'ETH']:
        # Криптовалюты - больше знаков после запятой
        return f"{amount:.6f} {currency_code}"
    else:
        # Фиатные валюты - стандартное форматирование
        return f"{amount:.2f} {currency_code}"

def safe_float_conversion(value: Any, default: float = 0.0) -> float:
    """Безопасное преобразование в float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default