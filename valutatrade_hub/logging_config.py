import logging
import os
from logging.handlers import RotatingFileHandler
from .infra.settings import settings

def setup_logging():
    """Настраивает систему логирования"""
    log_level = getattr(logging, settings.get('log_level', 'INFO'))
    log_file = settings.get('log_file', 'logs/actions.log')
    
    # Создаем директорию для логов
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Форматтер
    formatter = logging.Formatter(
        '%(levelname)s %(asctime)s %(name)s %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S'
    )
    
    # Файловый handler с ротацией
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=settings.get('max_log_size_mb', 10) * 1024 * 1024,
        backupCount=settings.get('backup_count', 5)
    )
    file_handler.setFormatter(formatter)
    
    # Консольный handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Логгер для действий
    action_logger = logging.getLogger('actions')
    action_logger.setLevel(log_level)

# Инициализация при импорте
setup_logging()