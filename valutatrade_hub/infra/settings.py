# valutatrade_hub/infra/settings.py
import os
import json
from typing import Any, Dict, Optional
from datetime import datetime

class SettingsLoader:
    """Singleton для загрузки и управления конфигурацией приложения"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsLoader, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._config: Dict[str, Any] = {}
            self._load_configuration()
            self._initialized = True
    
    def _load_configuration(self) -> None:
        """Загружает конфигурацию с значениями по умолчанию"""
        # Базовые настройки по умолчанию
        default_config = {
            'data_dir': 'data',
            'log_dir': 'logs',
            'rates_ttl_seconds': 300,
            'default_base_currency': 'USD',
            'log_level': 'INFO',
            'log_format': 'text',
            'log_file': 'actions.log',
            'max_log_size_mb': 10,
            'backup_count': 5,
            'min_password_length': 4,
            'supported_currencies': ['USD', 'EUR', 'RUB', 'BTC', 'ETH'],
        }
        
        self._config = default_config
        self._load_from_json_config()
        self._load_from_environment()
        self._ensure_directories()
    
    def _load_from_json_config(self) -> None:
        """Загружает конфигурацию из JSON файла если существует"""
        config_files = ['config.json', '../config.json']
        
        for config_file in config_files:
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        json_config = json.load(f)
                    self._config.update(json_config)
                    print(f"Configuration loaded from {config_file}")
                    break
                except Exception as e:
                    print(f"Warning: Could not load configuration from {config_file}: {e}")
    
    def _load_from_environment(self) -> None:
        """Переопределяет настройки переменными окружения"""
        env_mapping = {
            'VALUTATRADE_DATA_DIR': 'data_dir',
            'VALUTATRADE_LOG_DIR': 'log_dir', 
            'VALUTATRADE_RATES_TTL': 'rates_ttl_seconds',
            'VALUTATRADE_LOG_LEVEL': 'log_level',
        }
        
        for env_var, config_key in env_mapping.items():
            if env_var in os.environ:
                self._config[config_key] = os.environ[env_var]
    
    def _ensure_directories(self) -> None:
        """Создает необходимые директории"""
        directories = [
            self.get('data_dir'),
            self.get('log_dir'),
        ]
        
        for directory in directories:
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)
    
    def get_data_path(self, filename: str) -> str:
        data_dir = self.get('data_dir', 'data')
        return os.path.join(data_dir, filename)

# Глобальный экземпляр
settings = SettingsLoader()