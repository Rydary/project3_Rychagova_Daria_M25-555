import logging
from datetime import datetime
from typing import Dict, List, Tuple

from .api_clients import ExchangeRateAPIClient, CoinGeckoAPIClient
from .storage import RatesStorage
from .config import api_config

logger = logging.getLogger(__name__)

class RatesUpdater:
    """Основной класс для обновления курсов валют"""
    
    def __init__(self):
        self.exchangerate_client = ExchangeRateAPIClient()
        self.coingecko_client = CoinGeckoAPIClient()
        self.storage = RatesStorage()
        self.clients = {
            'coingecko': self.coingecko_client,
            'exchangerate': self.exchangerate_client
        }
    
    def run_update(self, sources: List[str] = None) -> Dict:
        """Основной метод обновления курсов (соответствует требованиям)"""
        logger.info("Starting rates update...")
        
        if sources is None:
            sources = list(self.clients.keys())
        
        all_rates = {}
        update_results = {
            'successful_sources': [],
            'failed_sources': [],
            'total_rates': 0,
            'last_refresh': datetime.now().isoformat()
        }
        
        timestamp = datetime.now()
        
        for source_name in sources:
            if source_name not in self.clients:
                logger.warning(f"Unknown source: {source_name}")
                continue
                
            client = self.clients[source_name]
            
            try:
                rates = client.fetch_rates()
                all_rates.update(rates)
                update_results['successful_sources'].append(source_name)
                logger.info(f"{source_name}: Successfully fetched {len(rates)} rates")
                
                for pair, rate in rates.items():
                    from_currency, to_currency = pair.split('_')
                    source_display = "CoinGecko" if source_name == "coingecko" else "ExchangeRate-API"
                    
                    meta = {}
                    if source_name == "coingecko":
                        meta = {"crypto_id": api_config.CRYPTO_CURRENCIES.get(from_currency)}
                    else:
                        meta = {"base_currency": api_config.BASE_CURRENCY}
                    
                    self.storage.save_exchange_rate_record(
                        from_currency, to_currency, rate, timestamp, 
                        source_display, meta
                    )
                
            except Exception as e:
                update_results['failed_sources'].append({
                    'source': source_name,
                    'error': str(e)
                })
                logger.error(f"{source_name}: Failed to fetch rates - {str(e)}")
        
        if all_rates:
            success = self.storage.save_rates_cache(all_rates, update_results['last_refresh'])
            if success:
                update_results['total_rates'] = len(all_rates)
                logger.info(f"Update completed: {len(all_rates)} rates from {len(update_results['successful_sources'])} sources")
            else:
                logger.error("Failed to save rates cache")
                update_results['failed_sources'].append({
                    'source': 'storage',
                    'error': 'Failed to save cache'
                })
        else:
            logger.warning("No rates were retrieved from any source")
        
        return update_results

    def update_all_rates(self) -> Tuple[bool, str]:
        """Совместимость со старым кодом"""
        results = self.run_update()
        
        if results['successful_sources']:
            msg = f"Successfully updated {results['total_rates']} rates from {len(results['successful_sources'])} sources"
            return True, msg
        else:
            msg = "No rates were retrieved from any source"
            if results['failed_sources']:
                errors = ", ".join([f"{f['source']}: {f['error']}" for f in results['failed_sources']])
                msg = f"Update failed: {errors}"
            return False, msg
    
    def get_update_status(self) -> Dict:
        """Возвращает статус последнего обновления"""
        cache_data = self.storage.load_rates_cache()
        
        if not cache_data or 'pairs' not in cache_data:
            return {
                "cache_exists": False,
                "message": "Cache is empty or not found",
                "last_update_currencies": 0,
                "total_records_in_journal": len(self.storage._load_all_records()),
                "is_stale": True
            }
        
        return {
            "cache_exists": True,
            "last_update_currencies": len(cache_data.get('pairs', {})),
            "total_records_in_journal": len(self.storage._load_all_records()),
            "last_refresh": cache_data.get('last_refresh', 'Unknown'),
            "is_stale": self.storage.is_cache_stale(),
            "cached_rates_sample": dict(list(cache_data.get('pairs', {}).items())[:3])
        }