import json
import os
from typing import Any, Dict, List
from threading import Lock
from .settings import settings

class DatabaseManager:
    """Singleton для управления JSON-хранилищем данных"""
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._data_dir = settings.get('data_dir', 'data')
            self._ensure_data_dir()
            self._initialized = True
    
    def _ensure_data_dir(self):
        """Создает директорию для данных если её нет"""
        os.makedirs(self._data_dir, exist_ok=True)
    
    def _get_file_path(self, collection: str) -> str:
        """Возвращает путь к файлу коллекции"""
        return os.path.join(self._data_dir, f"{collection}.json")
    
    def load_collection(self, collection: str) -> Dict[str, Any]:
        """Загружает данные коллекции из JSON файла"""
        file_path = self._get_file_path(collection)
        
        if not os.path.exists(file_path):
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Warning: Could not load {collection}: {e}")
            return {}
    
    def save_collection(self, collection: str, data: Dict[str, Any]):
        """Сохраняет данные коллекции в JSON файл"""
        file_path = self._get_file_path(collection)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"Error saving {collection}: {e}")
            raise
    
    def atomic_update(self, collection: str, update_fn) -> Any:
        """Атомарно обновляет коллекцию с блокировкой"""
        with self._lock:
            data = self.load_collection(collection)
            result = update_fn(data)
            self.save_collection(collection, data)
            return result

# Глобальный экземпляр базы данных
db = DatabaseManager()