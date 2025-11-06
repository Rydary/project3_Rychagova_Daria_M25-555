import time
import threading
import logging
from typing import Optional

from .updater import RatesUpdater
from .config import parser_config

logger = logging.getLogger(__name__)

class RatesScheduler:
    """Планировщик периодического обновления курсов"""
    
    def __init__(self):
        self.updater = RatesUpdater()
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    def start_scheduler(self) -> bool:
        """Запускает фоновый планировщик"""
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            logger.warning("Scheduler is already running")
            return False
        
        self._stop_event.clear()
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        
        logger.info(f"Scheduler started with {parser_config.UPDATE_INTERVAL_MINUTES} minute interval")
        return True
    
    def stop_scheduler(self) -> bool:
        """Останавливает планировщик"""
        if not self._scheduler_thread or not self._scheduler_thread.is_alive():
            logger.warning("Scheduler is not running")
            return False
        
        self._stop_event.set()
        self._scheduler_thread.join(timeout=10)
        
        logger.info("Scheduler stopped")
        return True
    
    def _scheduler_loop(self):
        """Основной цикл планировщика"""
        while not self._stop_event.is_set():
            try:
                # Выполняем обновление
                success, message = self.updater.update_all_rates()
                if success:
                    logger.info(f"Scheduled update completed: {message}")
                else:
                    logger.error(f"Scheduled update failed: {message}")
                
                # Ждем до следующего обновления
                wait_seconds = parser_config.UPDATE_INTERVAL_MINUTES * 60
                for _ in range(wait_seconds):
                    if self._stop_event.is_set():
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Scheduler loop error: {str(e)}")
                time.sleep(60)  # Ждем минуту при ошибке
    
    def run_once(self) -> tuple[bool, str]:
        """Выполняет одноразовое обновление"""
        return self.updater.update_all_rates()
    
    def get_status(self) -> dict:
        """Возвращает статус планировщика"""
        status = {
            "scheduler_running": self._scheduler_thread and self._scheduler_thread.is_alive(),
            "stop_requested": self._stop_event.is_set(),
        }
        status.update(self.updater.get_update_status())
        return status