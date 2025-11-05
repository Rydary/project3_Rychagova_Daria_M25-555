import json
import os
from datetime import datetime
from typing import Any, Dict

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