import json
import os
import tempfile
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from .config import parser_config, api_config

logger = logging.getLogger(__name__)

class RatesStorage:
    """Управление хранением курсов валют"""
    
    def __init__(self):
        self._ensure_data_directory()
    
    def _ensure_data_directory(self):
        """Создает директорию data если она не существует"""
        os.makedirs(os.path.dirname(parser_config.EXCHANGE_RATES_PATH), exist_ok=True)
        os.makedirs(os.path.dirname(parser_config.RATES_CACHE_PATH), exist_ok=True)
    
    def _generate_record_id(self, from_currency: str, to_currency: str, timestamp: datetime) -> str:
        """Генерирует уникальный ID записи"""
        iso_timestamp = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        return f"{from_currency}_{to_currency}_{iso_timestamp}"
    
    def save_exchange_rate_record(self, 
                                from_currency: str, 
                                to_currency: str, 
                                rate: float, 
                                timestamp: datetime,
                                source: str,
                                meta: Optional[Dict] = None) -> bool:
        """Сохраняет запись о курсе валют в журнал"""
        try:
            records = self.load_all_records()
            
            record = {
                "id": self._generate_record_id(from_currency, to_currency, timestamp),
                "from_currency": from_currency.upper(),
                "to_currency": to_currency.upper(),
                "rate": float(rate),
                "timestamp": timestamp.isoformat(),
                "source": source,
                "meta": meta or {}
            }
            
            records.append(record)
            
            with tempfile.NamedTemporaryFile(mode='w', 
                                           dir=os.path.dirname(parser_config.EXCHANGE_RATES_PATH),
                                           delete=False) as temp_file:
                json.dump(records, temp_file, indent=2, ensure_ascii=False)
                temp_path = temp_file.name
            
            os.replace(temp_path, parser_config.EXCHANGE_RATES_PATH)
            
            logger.info(f"Saved exchange rate record: {from_currency}->{to_currency} = {rate} from {source}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save exchange rate record: {str(e)}")
            return False
    
    def load_all_records(self) -> List[Dict]:
        """Загружает все записи из журнала"""
        try:
            if not os.path.exists(parser_config.EXCHANGE_RATES_PATH):
                return []
            
            with open(parser_config.EXCHANGE_RATES_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load exchange rates records: {str(e)}")
            return []
    
    def update_rates_cache(self, rates: Dict[str, float]) -> bool:
        """Обновляет кэш курсов для Core Service"""
        try:
            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "rates": rates,
                "base_currency": "USD"
            }

            with tempfile.NamedTemporaryFile(mode='w', 
                                           dir=os.path.dirname(parser_config.RATES_CACHE_PATH),
                                           delete=False) as temp_file:
                json.dump(cache_data, temp_file, indent=2, ensure_ascii=False)
                temp_path = temp_file.name
            
            os.replace(temp_path, parser_config.RATES_CACHE_PATH)
            
            logger.info(f"Updated rates cache with {len(rates)} currencies")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update rates cache: {str(e)}")
            return False
    
    def get_latest_rates(self) -> Dict[str, float]:
        """Получает последние курсы из кэша"""
        try:
            if not os.path.exists(parser_config.RATES_CACHE_PATH):
                return {}
            
            with open(parser_config.RATES_CACHE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('rates', {})
                
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load latest rates: {str(e)}")
            return {}
    
    def save_rates_cache(self, rates: Dict[str, float], last_refresh: str) -> bool:
        """Сохраняет курсы в кэш в НОВОМ формате согласно требованиям"""
        try:
            cache_data = {
                "pairs": {},
                "last_refresh": last_refresh
            }
    
            for pair, rate in rates.items():
                from_currency = pair.split('_')[0]
                source = "CoinGecko" if from_currency in api_config.CRYPTO_CURRENCIES else "ExchangeRate-API"
                
                cache_data["pairs"][pair] = {
                    "rate": float(rate),
                    "updated_at": last_refresh,
                    "source": source
                }
       
            with tempfile.NamedTemporaryFile(mode='w', 
                                           dir=os.path.dirname(parser_config.RATES_CACHE_PATH),
                                           delete=False,
                                           encoding='utf-8') as temp_file:
                json.dump(cache_data, temp_file, indent=2, ensure_ascii=False)
                temp_path = temp_file.name
            
            os.replace(temp_path, parser_config.RATES_CACHE_PATH)
            
            logger.info(f"Saved {len(rates)} rates to cache in new format (last_refresh: {last_refresh})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save rates cache in new format: {str(e)}")
            return False

    def load_rates_cache(self) -> Optional[Dict]:
        """Загружает кэш курсов в НОВОМ формате"""
        try:
            if not os.path.exists(parser_config.RATES_CACHE_PATH):
                return None
            
            with open(parser_config.RATES_CACHE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load rates cache: {str(e)}")
            return None

    def is_cache_stale(self) -> bool:
        """Проверяет, устарел ли кэш (по TTL)"""
        cache_data = self.load_rates_cache()
        if not cache_data or 'last_refresh' not in cache_data:
            return True
        
        try:
            last_refresh = datetime.fromisoformat(cache_data['last_refresh'].replace('Z', '+00:00'))
            stale_time = last_refresh + timedelta(minutes=parser_config.CACHE_TTL_MINUTES)
            return datetime.now().astimezone() > stale_time.astimezone()
        except (ValueError, TypeError) as e:
            logger.warning(f"Error checking cache staleness: {e}")
            return True
    
    # def get_latest_rates(self) -> Dict[str, float]:
    #     """Совместимость: получает последние курсы из кэша в СТАРОМ формате"""
    #     cache_data = self.load_rates_cache()
    #     if not cache_data or 'pairs' not in cache_data:
    #         return {}
    #     old_format_rates = {}
    #     for pair, data in cache_data.get('pairs', {}).items():
    #         currency = pair.split('_')[0] 
    #         old_format_rates[currency] = data['rate']
        
    #     return old_format_rates