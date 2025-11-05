import functools
import logging
from typing import Any, Callable, Dict
from datetime import datetime

def log_action(verbose: bool = False):
    """
    Декоратор для логирования доменных операций
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = logging.getLogger('actions')
            
            # Базовая информация для лога
            log_data = {
                'timestamp': datetime.now().isoformat(),
                'action': func.__name__.upper(),
                'args': args,
                'kwargs': kwargs
            }
            
            try:
                # Выполняем функцию
                result = func(*args, **kwargs)
                log_data['result'] = 'OK'
                
                # Дополнительная информация при verbose
                if verbose and hasattr(result, '__dict__'):
                    log_data['details'] = str(result)
                
                logger.info(_format_log_message(log_data))
                return result
                
            except Exception as e:
                # Логируем ошибку
                log_data['result'] = 'ERROR'
                log_data['error_type'] = type(e).__name__
                log_data['error_message'] = str(e)
                
                logger.error(_format_log_message(log_data))
                raise
        
        return wrapper
    return decorator

def _format_log_message(log_data: Dict[str, Any]) -> str:
    """Форматирует сообщение лога"""
    parts = [log_data['action']]
    
    # Добавляем базовую информацию
    if 'user_id' in log_data.get('kwargs', {}):
        parts.append(f"user='{log_data['kwargs']['user_id']}'")
    elif len(log_data['args']) > 1:
        parts.append(f"user='{log_data['args'][1]}'")  # предполагаем что user_id второй аргумент
    
    # Добавляем специфичные поля
    for field in ['currency_code', 'amount', 'from_code', 'to_code']:
        if field in log_data.get('kwargs', {}):
            value = log_data['kwargs'][field]
            parts.append(f"{field}='{value}'")
    
    # Добавляем результат
    parts.append(f"result={log_data['result']}")
    
    # Добавляем информацию об ошибке если есть
    if log_data['result'] == 'ERROR':
        parts.append(f"error={log_data['error_type']}:{log_data['error_message']}")
    
    return ' '.join(parts)